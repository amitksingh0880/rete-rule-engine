import { useState } from "react";
import Editor from "react-simple-code-editor";
import Prism from "prismjs";
import "prismjs/components/prism-yaml";
import "prismjs/themes/prism-tomorrow.css";
import axios from "axios";
import { Send, CheckCircle2, AlertCircle, Loader2, History } from "lucide-react";
import { cn } from "@/lib/utils";
import { AIAssistant } from "./ai-assistant";

const DEFAULT_DSL = `
rule "approve_policy"
  when
    Applicant(score >= 700)
    Applicant(income > 50000)
  then
    return(result="APPROVED", reason="High credit score and sufficient income")
`;

// Handle potential ESM/CJS default export differences
const CodeEditor = (Editor as any).default || Editor;

export function RuleEditor() {
  const [code, setCode] = useState(DEFAULT_DSL);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);

  const handleLoad = async () => {
    setLoading(true);
    setStatus(null);
    try {
      const res = await axios.post("http://localhost:8000/rules/load", { dsl: code });
      setStatus({ 
        type: 'success', 
        message: `Successfully loaded ${res.data.rules_loaded} rules: ${res.data.rule_ids.join(", ")}` 
      });
    } catch (err: any) {
      let message = "Failed to load rules. Check your syntax.";
      if (err.response?.data?.detail) {
        message = typeof err.response.data.detail === "string" 
          ? err.response.data.detail 
          : JSON.stringify(err.response.data.detail);
      }
      setStatus({ type: 'error', message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex gap-8 h-[calc(100vh-180px)]">
      <div className="flex-1 flex flex-col gap-6 min-w-0">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
               <History size={14} className="text-muted-foreground" />
               <span className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Workspace / Editor</span>
            </div>
            <h2 className="text-4xl font-bold tracking-tighter">DSL Architect</h2>
          </div>
          <button
            onClick={handleLoad}
            disabled={loading}
            className={cn(
              "flex items-center gap-3 px-8 py-3 bg-white text-black rounded-2xl font-black uppercase tracking-tighter transition-all shadow-[0_0_30px_-5px_RGBA(255,255,255,0.2)]",
              "hover:bg-primary hover:text-white hover:scale-105 active:scale-95 disabled:opacity-50"
            )}
          >
            {loading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
            {loading ? "Compiling..." : "Deploy Rule"}
          </button>
        </div>

        <div className="flex-1 glass-card rounded-[2.5rem] overflow-hidden border border-white/5 shadow-2xl flex flex-col">
          <div className="bg-white/5 px-8 py-4 border-b border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500/30" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/30" />
                <div className="w-3 h-3 rounded-full bg-green-500/30" />
              </div>
              <div className="h-4 w-px bg-white/10" />
              <span className="text-xs font-mono text-muted-foreground">logic_flow.dsl</span>
            </div>
            <div className="flex items-center gap-2">
               <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
               <span className="text-[10px] font-bold uppercase tracking-widest text-primary">Live Mode</span>
            </div>
          </div>
          <div className="flex-1 overflow-auto custom-scrollbar">
            <CodeEditor
              value={code}
              onValueChange={(c: string) => setCode(c)}
              highlight={(c: string) => Prism.highlight(c, Prism.languages.yaml || {}, "yaml")}
              padding={32}
              style={{
                fontFamily: '"Fira code", "Fira Mono", monospace',
                fontSize: 16,
                minHeight: "100%",
                backgroundColor: "transparent",
              }}
              className="outline-none"
            />
          </div>
        </div>

        {status && (
          <div className={cn(
            "p-5 rounded-3xl flex items-start gap-4 animate-in fade-in slide-in-from-top-4 duration-500",
            status.type === 'success' ? "bg-green-500/10 border border-green-500/20 text-green-400" : "bg-red-500/10 border border-red-500/20 text-red-400"
          )}>
            <div className={cn(
              "p-2 rounded-xl",
              status.type === 'success' ? "bg-green-500/20" : "bg-red-500/20"
            )}>
              {status.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
            </div>
            <div>
              <p className="font-bold text-sm tracking-tight">{status.type === 'success' ? "DEPLOYMENT SUCCESSFUL" : "DEPLOYMENT FAILED"}</p>
              <p className="text-xs opacity-70 font-medium leading-relaxed mt-1">{status.message}</p>
            </div>
          </div>
        )}
      </div>

      <AIAssistant onApplyDSL={(dsl) => setCode(prev => prev + "\n" + dsl)} />
    </div>
  );
}
