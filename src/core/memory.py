"""
Working Memory implementation for Rete algorithm.

WMEs (Working Memory Elements) are typed, immutable facts that flow through the
Rete network during forward-chaining inference.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import uuid


@dataclass(frozen=True)
class WME:
    """
    Immutable Working Memory Element representing a typed fact.

    Attributes:
        fact_type:  Category of fact (e.g. 'Applicant', 'Policy', 'Claim')
        attributes: Arbitrary key-value data (must be JSON-serialisable)
        timestamp:  UTC time the fact was created
        source:     Origin string – 'system', 'api', 'external', …
        id:         Unique identifier; auto-generated if not supplied
    """
    fact_type: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "system"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # -----------------------------------------------------------------------
    # Accessor helpers
    # -----------------------------------------------------------------------
    def get(self, attr: str, default: Any = None) -> Any:
        """Safely retrieve an attribute value."""
        return self.attributes.get(attr, default)

    def matches_type(self, fact_type: str) -> bool:
        return self.fact_type == fact_type

    # -----------------------------------------------------------------------
    # Serialisation
    # -----------------------------------------------------------------------
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "fact_type": self.fact_type,
            "attributes": self.attributes,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "WME":
        return cls(
            id=data["id"],
            fact_type=data["fact_type"],
            attributes=data["attributes"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source", "system"),
        )

    def __repr__(self) -> str:
        return f"WME({self.fact_type}#{self.id} {self.attributes})"


# ---------------------------------------------------------------------------
# Working Memory container
# ---------------------------------------------------------------------------

class WorkingMemory:
    """
    Container for all WMEs.

    Maintains three indexes for fast lookups:
      - ``_facts``           : id    → WME
      - ``_type_index``      : type  → set[id]
      - ``_attribute_index`` : attr  → value → set[id]
    """

    def __init__(self) -> None:
        self._facts: Dict[str, WME] = {}
        self._type_index: Dict[str, set] = {}
        self._attribute_index: Dict[str, Dict[Any, set]] = {}

    # -----------------------------------------------------------------------
    # Mutation
    # -----------------------------------------------------------------------
    def assert_fact(self, wme: WME) -> None:
        """Add a new fact. Raises ValueError if already present."""
        if wme.id in self._facts:
            raise ValueError(f"Fact {wme.id!r} already exists – use update_fact().")
        self._facts[wme.id] = wme
        self._index_fact(wme)

    def retract_fact(self, wme_id: str) -> Optional[WME]:
        """Remove a fact. Returns the WME, or None if not found."""
        wme = self._facts.pop(wme_id, None)
        if wme:
            self._unindex_fact(wme)
        return wme

    def update_fact(self, wme: WME) -> None:
        """Replace an existing fact (same id, updated data)."""
        old = self._facts.get(wme.id)
        if old:
            self._unindex_fact(old)
        self._facts[wme.id] = wme
        self._index_fact(wme)

    # -----------------------------------------------------------------------
    # Query
    # -----------------------------------------------------------------------
    def get_fact(self, wme_id: str) -> Optional[WME]:
        return self._facts.get(wme_id)

    def get_facts_by_type(self, fact_type: str) -> List[WME]:
        ids = self._type_index.get(fact_type, set())
        return [self._facts[i] for i in ids if i in self._facts]

    def get_facts_by_attribute(self, attr: str, value: Any) -> List[WME]:
        ids = self._attribute_index.get(attr, {}).get(value, set())
        return [self._facts[i] for i in ids if i in self._facts]

    def all_facts(self) -> List[WME]:
        return list(self._facts.values())

    # -----------------------------------------------------------------------
    # Housekeeping
    # -----------------------------------------------------------------------
    def clear(self) -> None:
        self._facts.clear()
        self._type_index.clear()
        self._attribute_index.clear()

    def __len__(self) -> int:
        return len(self._facts)

    def __repr__(self) -> str:
        return f"WorkingMemory({len(self._facts)} facts)"

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------
    def _index_fact(self, wme: WME) -> None:
        # Type index
        self._type_index.setdefault(wme.fact_type, set()).add(wme.id)
        # Attribute index
        for attr, value in wme.attributes.items():
            try:
                self._attribute_index.setdefault(attr, {}).setdefault(value, set()).add(wme.id)
            except TypeError:
                # unhashable value (e.g. list); skip attribute index for it
                pass

    def _unindex_fact(self, wme: WME) -> None:
        self._type_index.get(wme.fact_type, set()).discard(wme.id)
        for attr, value in wme.attributes.items():
            try:
                self._attribute_index.get(attr, {}).get(value, set()).discard(wme.id)
            except TypeError:
                pass
