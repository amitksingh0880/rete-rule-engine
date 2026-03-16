"""
FastAPI REST server for the Finance Rule Engine.

Endpoints
---------
POST /execute          – evaluate rules against facts
POST /rules/load       – load DSL rule text
GET  /rules            – list compiled rules
DELETE /rules/{id}     – remove a rule
GET  /health           – service health
GET  /metrics          – basic runtime metrics
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import yaml
from fastapi import BackgroundTasks, Body, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Internal imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.network import ReteNetwork
from dsl.compiler import DSLRuleEngine
from ai.feature_store import FeatureStore
from ai.model_registry import ModelRegistry
from ai.guardrails import GuardrailManager
from ai.inference import InferenceEngine
from persistence.audit_log import AuditLogger

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Pydantic schemas
# -----------------------------------------------------------------------

class FactInput(BaseModel):
    fact_type: str = Field(..., description="Fact category (Applicant, Policy, Claim, …)")
    attributes: Dict[str, Any] = Field(default_factory=dict)
    source: str = "api"

class ExecuteRequest(BaseModel):
    facts: List[FactInput]
    context: Dict[str, Any] = Field(default_factory=dict)
    trace: bool = False
    max_cycles: int = 100

class ExecuteResponse(BaseModel):
    request_id: str
    decision: Optional[str]
    confidence: Optional[float] = None
    matched_rules: List[str]
    actions: List[Dict]
    guardrail_violations: List[Dict] = []
    latency_ms: float
    trace: Optional[List[Dict]] = None

class RuleDefinition(BaseModel):
    dsl: str = Field(..., description="Rule DSL source text")

class AIGenerateRequest(BaseModel):
    prompt: str

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(config: Optional[Dict] = None) -> FastAPI:
    cfg = config or {}

    app = FastAPI(
        title="Finance Rule Engine API",
        description="AI-powered forward-chaining rule engine for financial / insurance decisions.",
        version="2.0.0",
        docs_url="/docs" if cfg.get("enable_docs", True) else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.get("cors_origins", ["http://localhost:5173", "http://127.0.0.1:5173", "*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Component wiring
    # -----------------------------------------------------------------------
    model_registry = ModelRegistry(registry_path=cfg.get("model_path", "./models"))
    feature_store = FeatureStore(backend=cfg.get("feature_backend", "memory"))
    guardrails = GuardrailManager(
        enabled=cfg.get("guardrails_enabled", True),
        confidence_threshold=cfg.get("confidence_threshold", 0.6),
    )
    inference_engine = InferenceEngine(model_registry, feature_store, guardrails)
    rule_engine = DSLRuleEngine()
    rule_engine.network.register_predict_handler(inference_engine.handle_predict)
    audit_logger = AuditLogger()

    # Attach to app state for access in route handlers
    app.state.rule_engine = rule_engine
    app.state.inference_engine = inference_engine
    app.state.guardrails = guardrails
    app.state.audit_logger = audit_logger
    app.state.start_time = time.time()
    app.state.request_count = 0
    app.state.decision_count = {}
    app.state.ai_requests = 0


    # -----------------------------------------------------------------------
    # Routes
    # -----------------------------------------------------------------------

    @app.post("/execute", response_model=ExecuteResponse, tags=["Execution"])
    async def execute_rules(request: Request, req: ExecuteRequest = Body(...), background: BackgroundTasks = BackgroundTasks()):
        """Evaluate loaded rules against the provided set of facts."""
        request_id = str(uuid.uuid4().hex)[:12]
        re_: DSLRuleEngine = request.app.state.rule_engine
        gm: GuardrailManager = request.app.state.guardrails
        al: AuditLogger = request.app.state.audit_logger
        request.app.state.request_count += 1

        start = time.perf_counter()

        try:
            fact_dicts = [f.model_dump() for f in req.facts]
            result = re_.execute(fact_dicts, max_cycles=req.max_cycles)
        except Exception as exc:
            logger.error("Execution error: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail=str(exc))

        # Guardrails
        violations = gm.evaluate(
            context=req.context,
            decision=result,
            rule_id=request_id,
        )
        if gm.should_block(violations):
            result["decision"] = "REFERRED"
            result.setdefault("data", {})["reason"] = "Guardrail violations detected"

        latency_ms = (time.perf_counter() - start) * 1000

        # Track decisions
        decision = result.get("decision")
        if decision:
            request.app.state.decision_count[decision] = (
                request.app.state.decision_count.get(decision, 0) + 1
            )

        # Async audit
        background.add_task(
            al.log_decision,
            request_id=request_id,
            facts=fact_dicts,
            result=result,
            violations=[v.to_dict() for v in violations],
            latency_ms=latency_ms,
        )

        return ExecuteResponse(
            request_id=request_id,
            decision=result.get("decision"),
            matched_rules=result.get("matched_rules", []),
            actions=result.get("actions", []),
            guardrail_violations=[v.to_dict() for v in violations],
            latency_ms=round(float(latency_ms), 3),
            trace=result.get("actions") if req.trace else None,
        )

    @app.post("/rules/load", tags=["Rules"], status_code=status.HTTP_201_CREATED)
    async def load_rules(request: Request, definition: RuleDefinition = Body(...)):
        """Compile and load rules from DSL source."""
        re_: DSLRuleEngine = request.app.state.rule_engine
        try:
            rule_ids = re_.load_rules(definition.dsl)
        except SyntaxError as exc:
            raise HTTPException(status_code=400, detail=f"Syntax error: {exc}")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        return {"status": "created", "rules_loaded": len(rule_ids), "rule_ids": rule_ids}

    @app.post("/ai/generate", tags=["AI"])
    @app.post("/ai/generate/", tags=["AI"])
    async def generate_rule_ai(request: Request, req: AIGenerateRequest = Body(...)):
        """Mock AI endpoint to generate DSL from natural language."""
        request.app.state.ai_requests += 1
        logger.info(f"AI Generation requested: {req.prompt}")
        p = req.prompt.lower()
        if "credit" in p or "score" in p:
            dsl = 'rule "credit_check"\n  when\n    Applicant(score < 700)\n  then\n    return(result="REJECTED", reason="Score too low")'
        elif "income" in p:
            dsl = 'rule "income_check"\n  when\n    Applicant(income < 30000)\n  then\n    return(result="REVIEW", reason="Low income")'
        else:
            dsl = 'rule "new_logic"\n  when\n    # Auto-generated condition\n    Applicant(age > 18)\n  then\n    return(result="APPROVED")'
        
        return {"dsl": dsl}

    @app.get("/rules", tags=["Rules"])
    async def list_rules(request: Request):
        """List all compiled rules."""
        re_: DSLRuleEngine = request.app.state.rule_engine
        return {
            "count": len(re_.rule_ids),
            "rules": [
                {"id": rid, "has_source": rid in re_._rule_sources}
                for rid in re_.rule_ids
            ],
        }

    @app.get("/rules/{rule_id}/source", tags=["Rules"])
    async def get_rule_source(rule_id: str, request: Request):
        """Retrieve DSL source for a compiled rule."""
        re_: DSLRuleEngine = request.app.state.rule_engine
        src = re_.get_rule_source(rule_id)
        if src is None:
            raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")
        return {"rule_id": rule_id, "source": src}

    @app.get("/health", tags=["Operations"])
    async def health(request: Request):
        fs = request.app.state.rule_engine
        return {
            "status": "healthy",
            "uptime_seconds": round(float(time.time() - request.app.state.start_time), 1),
            "rules_loaded": len(request.app.state.rule_engine.rule_ids),
        }

    @app.get("/metrics", tags=["Operations"])
    async def metrics(request: Request):
        return {
            "requests_total": request.app.state.request_count,
            "decisions": request.app.state.decision_count,
            "rules_loaded": len(request.app.state.rule_engine.rule_ids),
            "uptime_seconds": round(float(time.time() - request.app.state.start_time), 1),
        }

    @app.get("/network", tags=["Rules"])
    async def get_network(request: Request):
        """Export the Rete network graph for visualization."""
        re_: DSLRuleEngine = request.app.state.rule_engine
        return re_.network.export_graph()

    return app


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    import uvicorn
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "../../config/default.yaml")
    cfg: Dict = {}
    if os.path.exists(config_path):
        with open(config_path) as f:
            full_cfg = yaml.safe_load(f)
            cfg = full_cfg.get("api", {})

    app = create_app(cfg)
    uvicorn.run(app, host=cfg.get("host", "0.0.0.0"), port=cfg.get("port", 8000))


if __name__ == "__main__":
    main()
