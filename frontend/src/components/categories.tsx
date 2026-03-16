import { useState } from "react";
import { 
  Database, 
  Plus, 
  Search, 
  Tag, 
  Trash2, 
  ChevronRight, 
  Fingerprint,
  Type,
  ToggleLeft
} from "lucide-react";

interface Attribute {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean';
  description: string;
}

interface Category {
  id: string;
  name: string;
  attributes: Attribute[];
}

export function Categories() {
  const [categories] = useState<Category[]>([
    {
      id: "cat_1",
      name: "Applicant Profile",
      attributes: [
        { id: "attr_1", name: "credit_score", type: "number", description: "FICO Credit Score" },
        { id: "attr_2", name: "annual_income", type: "number", description: "Gross yearly income" },
        { id: "attr_3", name: "employment_status", type: "string", description: "Current work status" },
      ]
    },
    {
      id: "cat_2",
      name: "Transaction Metadata",
      attributes: [
        { id: "attr_4", name: "amount", type: "number", description: "Transaction value in USD" },
        { id: "attr_5", name: "is_international", type: "boolean", description: "Cross-border flag" },
      ]
    }
  ]);

  const [search, setSearch] = useState("");

  const filteredCategories = categories.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.attributes.some(a => a.name.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="px-2 py-0.5 bg-indigo-500/20 text-indigo-400 text-[10px] font-black rounded uppercase tracking-tighter border border-indigo-500/20">
              Data Modeling
            </div>
          </div>
          <h2 className="text-5xl font-bold tracking-tighter">Attributes & Categories</h2>
          <p className="text-muted-foreground mt-2 font-medium">Define the data structure that your rules will monitor and evaluate.</p>
        </div>
        <button className="flex items-center gap-2 px-6 py-3 bg-white text-black rounded-2xl font-black uppercase tracking-tighter shadow-xl hover:scale-105 active:scale-95 transition-all text-xs">
          <Plus size={16} />
          Create Category
        </button>
      </div>

      <div className="relative group max-w-xl">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={18} />
        <input 
          type="text" 
          placeholder="Search attributes by name, description, or type..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all font-medium"
        />
      </div>

      <div className="grid grid-cols-1 gap-6">
        {filteredCategories.map((cat) => (
          <div key={cat.id} className="glass-card rounded-[2.5rem] border-white/5 bg-white/5 overflow-hidden group hover:bg-white/[0.07] transition-all">
            <div className="p-8 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-indigo-500/20 rounded-2xl flex items-center justify-center text-indigo-400">
                  <Database size={24} />
                </div>
                <div>
                  <h3 className="text-xl font-bold tracking-tight">{cat.name}</h3>
                  <p className="text-xs text-muted-foreground font-mono">{cat.attributes.length} defined attributes</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button className="p-2 text-muted-foreground hover:text-white transition-colors">
                  <Plus size={20} />
                </button>
                <button className="p-2 text-muted-foreground hover:text-red-400 transition-colors">
                  <Trash2 size={20} />
                </button>
              </div>
            </div>

            <div className="p-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {cat.attributes.map((attr) => (
                <div key={attr.id} className="p-5 bg-black/40 rounded-3xl border border-white/5 hover:border-primary/30 transition-all cursor-default group/item">
                  <div className="flex items-center justify-between mb-4">
                    <div className="px-2 py-1 bg-white/5 rounded-lg flex items-center gap-2">
                      {attr.type === 'number' && <Fingerprint size={12} className="text-orange-400" />}
                      {attr.type === 'string' && <Type size={12} className="text-blue-400" />}
                      {attr.type === 'boolean' && <ToggleLeft size={12} className="text-green-400" />}
                      <span className="text-[10px] font-black uppercase opacity-60 tracking-widest">{attr.type}</span>
                    </div>
                    <Tag size={14} className="text-muted-foreground opacity-0 group-hover/item:opacity-100 transition-opacity" />
                  </div>
                  <h4 className="font-bold text-white mb-1 group-hover/item:text-primary transition-colors">{attr.name}</h4>
                  <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">{attr.description}</p>
                  
                  <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between opacity-0 group-hover/item:opacity-100 transition-opacity">
                     <span className="text-[10px] font-black uppercase tracking-tighter text-indigo-400">View Usages</span>
                     <ChevronRight size={14} className="text-indigo-400" />
                  </div>
                </div>
              ))}
              <button className="border-2 border-dashed border-white/5 rounded-3xl flex flex-col items-center justify-center gap-3 p-6 text-muted-foreground hover:border-primary/40 hover:text-primary transition-all group/add">
                <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center group-hover/add:bg-primary/20 transition-colors">
                  <Plus size={20} />
                </div>
                <span className="text-xs font-bold uppercase tracking-widest">Add Attribute</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
