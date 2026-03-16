import { useState } from "react";
import Editor from "react-simple-code-editor";
import Prism from "prismjs";
import "prismjs/components/prism-json";
import "prismjs/themes/prism-tomorrow.css";
import axios from "axios";
import { 
  Play, 
  Trash2, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Zap, 
  Cpu, 
  History,
  Braces
} from "lucide-react";
import { cn } from "@/lib/utils";

const DEFAULT_FACTS = JSON.stringify([
  {
    "fact_type": "Applicant",
    "attributes": {
      "score": 750,
      "income": 60000,
      "age": 30
    }
  }
], null, 2);

const CodeEditor = (Editor as any).default || Editor;

export function ExecutionPlayground() {
  const [json, setJson] = useState(DEFAULT_FACTS);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExecute = async () => {
    setLoading(true);
    setError(null);
    try {
      const facts = JSON.parse(json);
      const res = await axios.post("http://localhost:8000/execute", { facts });
      setResult(res.data);
    } catch (err: any) {
      let msg = err instanceof SyntaxError ? "Invalid JSON format" : "Execution failed";
      if (err.response?.data?.detail) {
        msg = typeof err.response.data.detail === "string" 
          ? err.response.data.detail 
          : JSON.stringify(err.response.data.detail);
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="px-2 py-0.5 bg-orange-500/20 text-orange-400 text-[10px] font-black rounded uppercase tracking-tighter border border-orange-500/20">
              Live Testing
            </div>
          </div>
          <h2 className="text-5xl font-bold tracking-tighter">Inference Lab</h2>
          <p className="text-muted-foreground mt-2 font-medium">Inject facts and observe real-time decisioning outcomes.</p>
        </div>
        <div className="flex gap-4">
          <button 
            onClick={() => setJson(DEFAULT_FACTS)}
            className="p-3 bg-white/5 border border-white/5 rounded-2xl text-white/50 hover:text-white transition-colors"
          >
            <History size={20} />
          </button>
          <button 
            onClick={handleExecute}
            disabled={loading}
            className="flex items-center gap-3 px-8 py-3 bg-white text-black rounded-2xl font-black uppercase tracking-tighter shadow-xl hover:scale-105 active:scale-95 disabled:opacity-50 transition-all"
          >
            {loading ? <Loader2 className="animate-spin" size={20} /> : <Zap size={20} fill="currentColor" />}
            Run Inference
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="flex flex-col gap-4">
           <div className="flex items-center gap-2 px-2">
             <Braces size={16} className="text-primary" />
             <span className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground">Input Schema</span>
           </div>
           <div className="flex-1 glass-card rounded-[2.5rem] overflow-hidden border border-white/5 bg-black/40 min-h-[400px] flex flex-col">
              <div className="p-6 bg-white/5 border-b border-white/5 flex items-center justify-between">
                <span className="text-xs font-mono text-muted-foreground">facts.json</span>
                <Trash2 size={14} className="text-muted-foreground cursor-pointer hover:text-red-400 transition-colors" onClick={() => setJson("[]")} />
              </div>
              <div className="flex-1 overflow-auto custom-scrollbar p-6">
                <CodeEditor
                  value={json}
                  onValueChange={(c: string) => setJson(c)}
                  highlight={(c: string) => Prism.highlight(c, Prism.languages.json || {}, "json")}
                  padding={10}
                  style={{
                    fontFamily: '"Fira code", "Fira Mono", monospace',
                    fontSize: 14,
                    minHeight: "100%",
                  }}
                  className="outline-none"
                />
              </div>
           </div>
        </div>

        <div className="flex flex-col gap-4">
           <div className="flex items-center gap-2 px-2">
             <Cpu size={16} className="text-primary" />
             <span className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground">Execution Result</span>
           </div>
           <div className="flex-1 glass-card rounded-[2.5rem] border border-white/5 bg-black/40 p-8 flex flex-col min-h-[400px]">
             {result ? (
               <div className="h-full flex flex-col gap-6 animate-in fade-in slide-in-from-right-4">
                 <div className="flex items-center justify-between p-6 bg-primary/10 rounded-[2rem] border border-primary/20">
                    <div>
                      <p className="text-[10px] font-black text-primary uppercase tracking-widest mb-1">Final Decision</p>
                      <h4 className="text-3xl font-black text-white tracking-tighter">{result.decision || "NO_MATCH"}</h4>
                    </div>
                    <div className="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center text-white shadow-lg shadow-primary/20">
                       <CheckCircle2 size={24} />
                    </div>
                 </div>

                 <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-white/5 rounded-2xl border border-white/5">
                       <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Latency</p>
                       <p className="text-xl font-black text-white">{result.latency_ms}ms</p>
                    </div>
                    <div className="p-4 bg-white/5 rounded-2xl border border-white/5">
                       <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">Rules Matched</p>
                       <p className="text-xl font-black text-white">{result.matched_rules.length}</p>
                    </div>
                 </div>

                 <div className="flex-1 space-y-3 overflow-y-auto max-h-[150px] custom-scrollbar">
                    <p className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">Matched Rule IDs</p>
                    {result.matched_rules.map((rule: string) => (
                      <div key={rule} className="flex items-center gap-2 text-xs font-mono text-white/80 bg-white/5 p-2 rounded-lg border border-white/5">
                        <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                        {rule}
                      </div>
                    ))}
                 </div>
               </div>
             ) : error ? (
               <div className="h-full flex flex-col items-center justify-center text-center gap-4 text-red-400">
                  <AlertCircle size={48} className="opacity-50" />
                  <div>
                    <p className="font-black uppercase tracking-widest">Error Detected</p>
                    <p className="text-xs opacity-70 mt-1 max-w-[200px]">{error}</p>
                  </div>
               </div>
             ) : (
               <div className="h-full flex flex-col items-center justify-center text-center gap-4 opacity-30">
                  <Play size={48} fill="currentColor" />
                  <p className="text-xs font-black uppercase tracking-widest">Awaiting Inference</p>
               </div>
             )}
           </div>
        </div>
      </div>
    </div>
  );
}
