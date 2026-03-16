import { useEffect, useState } from "react";
import axios from "axios";
import { List, Trash2, Eye, Search, Filter } from "lucide-react";

export function RuleList() {
  const [rules, setRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    try {
      const res = await axios.get("http://localhost:8000/rules");
      setRules(res.data.rules);
    } catch (err) {
      console.error("Failed to fetch rules", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold">Compiled Rules</h2>
          <p className="text-muted-foreground">Manage and inspect all rules currently active in the engine.</p>
        </div>
        <div className="flex gap-4">
          <div className="relative group">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" />
            <input 
              type="text" 
              placeholder="Search rules..." 
              className="bg-white/5 border border-white/5 rounded-xl pl-10 pr-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all w-64"
            />
          </div>
          <button className="p-2.5 bg-white/5 border border-white/5 rounded-xl hover:bg-white/10 transition-all">
            <Filter size={20} className="text-muted-foreground" />
          </button>
        </div>
      </div>

      <div className="glass-card rounded-2xl overflow-hidden shadow-2xl">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-white/5 border-b border-white/5 text-xs uppercase tracking-wider text-muted-foreground font-semibold">
              <th className="px-6 py-4">Rule Identifier</th>
              <th className="px-6 py-4">Source Available</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {loading ? (
              [1, 2, 3].map((i) => (
                <tr key={i} className="animate-pulse">
                  <td className="px-6 py-6"><div className="h-4 bg-white/5 rounded w-2/3" /></td>
                  <td className="px-6 py-6"><div className="h-4 bg-white/5 rounded w-1/4" /></td>
                  <td className="px-6 py-6 text-right"><div className="h-8 bg-white/5 rounded w-24 ml-auto" /></td>
                </tr>
              ))
            ) : rules.length > 0 ? (
              rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="px-6 py-4 font-mono text-sm tracking-tight">{rule.id}</td>
                  <td className="px-6 py-4">
                    {rule.has_source ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/20">
                        YES
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
                        NO
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-2 hover:bg-primary/20 hover:text-primary rounded-lg transition-all text-muted-foreground">
                        <Eye size={18} />
                      </button>
                      <button className="p-2 hover:bg-red-500/20 hover:text-red-500 rounded-lg transition-all text-muted-foreground">
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={3} className="px-6 py-20 text-center text-muted-foreground">
                  <div className="flex flex-col items-center gap-3">
                    <List size={48} className="text-white/5" />
                    <p>No rules found. Start by loading some from the Editor.</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
