import { 
  LayoutDashboard, 
  FileCode2, 
  ListTree, 
  PlayCircle, 
  Settings, 
  Database,
  BarChart3,
  Network
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "editor", label: "Rule Architect", icon: FileCode2 },
    { id: "list", label: "Policies", icon: ListTree },
    { id: "deployment", label: "Deployments", icon: PlayCircle }, // Renamed from playground
    { id: "flow", label: "Logic Flow", icon: Network },
    { id: "categories", label: "Data Schema", icon: Database },
    { id: "analytics", label: "Intelligence", icon: BarChart3 },
    { id: "settings", label: "Settings", icon: Settings },

  ];

  return (
    <div className="w-72 h-screen bg-card/40 backdrop-blur-xl border-r border-white/5 flex flex-col p-6 fixed left-0 top-0 z-50">
      <div className="flex items-center gap-3 mb-10 px-2">
        <div className="w-10 h-10 bg-linear-to-tr from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-500/20">
          <Network className="text-white" size={24} />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tighter bg-clip-text text-transparent bg-linear-to-r from-white to-white/60">
            FRE Engine
          </h1>
          <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground font-black">
            Automated logic
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={cn(
              "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group relative overflow-hidden",
              activeTab === item.id 
                ? "bg-white/10 text-white shadow-inner border border-white/10" 
                : "text-muted-foreground hover:text-white hover:bg-white/5"
            )}
          >
            {activeTab === item.id && (
              <div className="absolute left-0 w-1 h-6 bg-primary rounded-r-full group-hover:h-8 transition-all" />
            )}
            <item.icon size={20} className={cn(
              "transition-colors",
              activeTab === item.id ? "text-primary" : "group-hover:text-white"
            )} />
            <span className="text-sm font-medium tracking-tight">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="mt-auto p-4 glass-card rounded-2xl border-white/5 bg-white/5 overflow-hidden group">
        <div className="relative z-10">
          <p className="text-xs font-bold text-white mb-1 group-hover:text-primary transition-colors">AI Status</p>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <p className="text-[10px] text-muted-foreground font-mono">Ready for generation</p>
          </div>
        </div>
        <div className="absolute -right-4 -bottom-4 w-16 h-16 bg-primary/10 rounded-full blur-2xl group-hover:bg-primary/20 transition-all" />
      </div>
    </div>
  );
}
