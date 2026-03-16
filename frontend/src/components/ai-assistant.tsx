import { useState } from "react";
import { Sparkles, Send, Bot, User, Loader2, Wand2 } from "lucide-react";
import axios from "axios";
import { cn } from "@/lib/utils";

interface AIAssistantProps {
  onApplyDSL: (dsl: string) => void;
}

export function AIAssistant({ onApplyDSL }: AIAssistantProps) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant', content: string, dsl?: string }[]>([
    { role: 'assistant', content: "Hi! I'm your AI Rule Architect. Tell me what logic you want to build, and I'll generate the DSL for you." }
  ]);

  const handleSend = async () => {
    if (!prompt.trim()) return;

    const userMsg = { role: 'user' as const, content: prompt };
    setMessages(prev => [...prev, userMsg]);
    setPrompt("");
    setLoading(true);

    try {
      const res = await axios.post("http://localhost:8000/ai/generate", { prompt });
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: "I've drafted a rule based on your requirements. You can review it below and apply it to the editor.",
        dsl: res.data.dsl
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: "Sorry, I encountered an error while generating the rule. Please check the backend connectivity." 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-96 flex flex-col glass-card border-none bg-white/5 h-full rounded-[2rem] overflow-hidden shadow-2xl">
      <div className="p-6 border-b border-white/5 bg-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
            <Sparkles className="text-primary size={18}" />
          </div>
          <span className="font-black uppercase tracking-tighter">AI Assistant</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-widest">Beta</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg, i) => (
          <div key={i} className={cn(
            "flex flex-col gap-2 animate-in fade-in slide-in-from-bottom-2",
            msg.role === 'user' ? "items-end" : "items-start"
          )}>
            <div className={cn(
              "max-w-[85%] p-4 rounded-3xl text-sm leading-relaxed",
              msg.role === 'user' 
                ? "bg-primary text-white rounded-tr-none shadow-lg shadow-primary/20" 
                : "bg-white/5 border border-white/10 text-white/80 rounded-tl-none"
            )}>
              <div className="flex items-center gap-2 mb-2">
                {msg.role === 'assistant' ? <Bot size={14} className="text-primary" /> : <User size={14} />}
                <span className="text-[10px] font-black uppercase opacity-50">
                  {msg.role === 'assistant' ? "Architect" : "You"}
                </span>
              </div>
              {msg.content}
            </div>

            {msg.dsl && (
              <div className="w-full mt-2 p-4 bg-black/40 border border-white/5 rounded-2xl font-mono text-[11px] relative group">
                <pre className="text-primary/90 whitespace-pre-wrap">{msg.dsl}</pre>
                <button
                  onClick={() => onApplyDSL(msg.dsl!)}
                  className="absolute right-2 bottom-2 p-2 bg-white/10 hover:bg-primary transition-all rounded-lg opacity-0 group-hover:opacity-100 flex items-center gap-2 text-[10px] font-bold"
                >
                  <Wand2 size={12} />
                  Apply
                </button>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-3 text-muted-foreground">
            <Loader2 className="animate-spin" size={16} />
            <span className="text-xs font-medium">Generating logic...</span>
          </div>
        )}
      </div>

      <div className="p-6 bg-white/5 border-t border-white/5">
        <div className="relative">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())}
            placeholder="Type your rule requirements..."
            className="w-full bg-white/5 border border-white/10 rounded-2xl p-4 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all resize-none min-h-[100px]"
          />
          <button
            onClick={handleSend}
            disabled={loading || !prompt.trim()}
            className="absolute right-3 bottom-3 p-2 bg-primary text-white rounded-xl hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 transition-all"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
