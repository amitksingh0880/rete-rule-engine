import { useEffect, useState } from "react";
import axios from "axios";
import { 
  Activity, 
  CheckCircle2, 
  Clock, 
  Layers, 
  TrendingUp, 
  Zap,
  ShieldCheck,
  Cpu,
  AlertTriangle
} from "lucide-react";
import { cn } from "@/lib/utils";

const StatTrendUp = () => (
  <div className="flex items-center gap-1 text-green-400 bg-green-400/10 px-2 py-1 rounded-full text-[10px] font-bold">
    <TrendingUp size={10} />
    <span>+12%</span>
  </div>
);

const StatCard = ({ title, value, icon: Icon, color, trend = true }: any) => (
  <div className="glass-card p-6 rounded-3xl border border-white/5 bg-white/5 hover:bg-white/10 transition-all hover:scale-[1.02] group relative overflow-hidden">
    <div className="flex items-center justify-between mb-4 relative z-10">
      <div className={cn("p-2.5 rounded-xl bg-white/5", color)}>
        <Icon size={24} />
      </div>
      {trend && <StatTrendUp />}
    </div>
    <div className="relative z-10">
      <p className="text-xs text-muted-foreground font-black uppercase tracking-widest mb-1">{title}</p>
      <h3 className="text-4xl font-bold tracking-tighter">{value}</h3>
    </div>
    <div className="absolute -right-8 -bottom-8 w-24 h-24 bg-white/5 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity" />
  </div>
);

export function Dashboard() {
  const [metrics, setMetrics] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [mRes, hRes] = await Promise.all([
          axios.get("http://localhost:8000/metrics"),
          axios.get("http://localhost:8000/health")
        ]);
        setMetrics(mRes.data);
        setHealth(hRes.data);
      } catch (err) {
        console.error("Failed to fetch metrics", err);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-10 max-w-7xl mx-auto">
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="px-2 py-0.5 bg-primary/20 text-primary text-[10px] font-black rounded uppercase tracking-tighter border border-primary/20">
              Live Monitoring
            </div>
          </div>
          <h2 className="text-5xl font-bold tracking-tighter text-white">Rule Control Center</h2>
          <p className="text-muted-foreground mt-2 font-medium">Real-time inference and network health analysis.</p>
        </div>
        <div className="flex gap-4">
           {health?.status === "healthy" ? (
             <div className="flex items-center gap-2 px-4 py-2 glass-card rounded-2xl border-green-500/20 bg-green-500/5 text-green-400">
               <ShieldCheck size={18} />
               <span className="text-sm font-bold">System Secure</span>
             </div>
           ) : (
             <div className="flex items-center gap-2 px-4 py-2 glass-card rounded-2xl border-yellow-500/20 bg-yellow-500/5 text-yellow-500">
               <AlertTriangle size={18} />
               <span className="text-sm font-bold">Checking Connectivity</span>
             </div>
           )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Total Inferences" 
          value={metrics?.requests_total ?? 0} 
          icon={Activity} 
          color="text-blue-400" 
        />
        <StatCard 
          title="Active Rules" 
          value={metrics?.rules_loaded ?? 0} 
          icon={Cpu} 
          color="text-purple-400" 
        />
        <StatCard 
          title="System Uptime" 
          value={metrics?.uptime_seconds ? `${metrics.uptime_seconds}s` : "0s"} 
          icon={Clock} 
          color="text-green-400" 
          trend={false}
        />
        <StatCard 
          title="Avg Latency" 
          value="0.14ms" 
          icon={Zap} 
          color="text-orange-400" 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 glass-card rounded-[2.5rem] p-10 border-white/5 relative overflow-hidden min-h-[450px]">
          <div className="relative z-10 flex flex-col h-full">
            <h3 className="text-2xl font-bold mb-8 flex items-center gap-2">
              <Layers size={24} className="text-primary" />
              Recent Decisions
            </h3>
            <div className="flex-1 space-y-4">
              {metrics?.decisions && Object.entries(metrics.decisions).length > 0 ? (
                Object.entries(metrics.decisions).map(([decision, count]: [string, any]) => (
                  <div key={decision} className="flex items-center justify-between p-6 bg-white/5 rounded-3xl border border-white/5 hover:bg-white/10 transition-all hover:translate-x-1 group">
                    <div className="flex items-center gap-4">
                      <div className={cn(
                        "w-3 h-3 rounded-full animate-pulse shadow-[0_0_15px]",
                        decision === "APPROVED" ? "bg-green-400 shadow-green-400/50" : "bg-purple-400 shadow-purple-400/50"
                      )} />
                      <span className="font-black uppercase tracking-tighter text-xl text-white/80 group-hover:text-white transition-colors">{decision}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-2xl font-black text-primary">{count}</span>
                      <p className="text-[10px] text-muted-foreground uppercase font-bold">Events</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground italic gap-4">
                  <Activity size={48} className="text-white/5" />
                  <p>Monitoring active network... waiting for first inference.</p>
                </div>
              )}
            </div>
          </div>
          <div className="absolute top-0 right-0 w-96 h-96 bg-primary/5 rounded-full blur-[100px] -mr-48 -mt-48" />
        </div>

        <div className="glass-card rounded-[2.5rem] p-10 border-white/5 bg-linear-to-b from-white/5 to-transparent flex flex-col">
          <div className="w-20 h-20 bg-primary/10 rounded-[2rem] flex items-center justify-center mb-8 shadow-inner border border-primary/20">
            <CheckCircle2 size={40} className="text-primary" />
          </div>
          <h3 className="text-3xl font-black tracking-tighter mb-4 text-white">High Efficiency Protocol</h3>
          <p className="text-muted-foreground leading-relaxed font-medium">
            The Rete network is optimized for sub-millisecond fact processing. All Alpha and Beta nodes are currently synchronized across the memory clusters.
          </p>
          
          <div className="mt-auto space-y-4 pt-8 border-t border-white/5">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Network Load</span>
              <span className="text-white font-mono">1.2%</span>
            </div>
            <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
               <div className="w-[12%] h-full bg-primary" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
