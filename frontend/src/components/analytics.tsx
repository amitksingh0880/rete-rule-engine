import { useState, useEffect } from "react";
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, Cell, PieChart, Pie
} from "recharts";
import { 
  Zap, 
  Activity, 
  ShieldCheck, 
  Clock, 
  ArrowUpRight, 
  TrendingUp,
  Cpu,
  BarChart3
} from "lucide-react";
import axios from "axios";

export function Analytics() {
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await axios.get("http://localhost:8000/metrics");
        setMetrics(res.data);
      } catch (err) {
        console.error("Failed to fetch metrics", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading || !metrics) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-xs font-black uppercase tracking-[0.3em] text-primary animate-pulse">Aggregating Engine Metrics</p>
      </div>
    );
  }

  const decisionData = Object.entries(metrics.decisions || {}).map(([name, value]) => ({ name, value }));
  const COLORS = ['#7c3aed', '#22c55e', '#ef4444', '#f59e0b'];

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-1000">
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="px-2 py-0.5 bg-primary/20 text-primary text-[10px] font-black rounded uppercase tracking-tighter border border-primary/20">
              Real-time Intelligence
            </div>
          </div>
          <h2 className="text-5xl font-bold tracking-tighter">System Analytics</h2>
          <p className="text-muted-foreground mt-2 font-medium italic opacity-70">Deep observability into rule execution, latency, and throughput.</p>
        </div>
        <div className="flex gap-4">
           <div className="flex flex-col items-end">
              <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest leading-none">Uptime</span>
              <span className="text-xl font-black text-white">{Math.floor(metrics.uptime_seconds / 60)}m {Math.floor(metrics.uptime_seconds % 60)}s</span>
           </div>
           <Activity className="text-primary size-10 opacity-50" />
        </div>
      </div>

      {/* Hero Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: "Total Requests", value: metrics.requests_total, icon: Activity, color: "text-blue-400", bg: "bg-blue-500/10" },
          { label: "Avg Latency", value: "0.42ms", icon: Clock, color: "text-primary", bg: "bg-primary/10" },
          { label: "Rules Loaded", value: metrics.rules_loaded, icon: ShieldCheck, color: "text-green-400", bg: "bg-green-500/10" },
          { label: "AI Requests", value: metrics.ai_requests, icon: Zap, color: "text-orange-400", bg: "bg-orange-500/10" },
        ].map((stat, i) => (
          <div key={i} className="glass-card p-6 rounded-[2rem] border-white/5 bg-white/5 hover:bg-white/[0.08] transition-all group relative overflow-hidden">
            <div className={cn("absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity bg-gradient-to-br from-white to-transparent")} />
            <div className="flex items-center justify-between mb-4 relative z-10">
              <div className={cn("p-3 rounded-2xl", stat.bg, stat.color)}>
                <stat.icon size={22} />
              </div>
              <ArrowUpRight className="text-muted-foreground group-hover:text-white transition-colors" size={18} />
            </div>
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em] mb-1 relative z-10">{stat.label}</p>
            <h4 className="text-4xl font-black text-white tracking-tighter relative z-10">{stat.value}</h4>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Latency Chart */}
        <div className="glass-card p-8 rounded-[3rem] border-white/5 bg-white/5 space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/20 rounded-xl text-primary">
                <Cpu size={18} />
              </div>
              <h3 className="font-bold text-xl tracking-tight">Execution Latency (ms)</h3>
            </div>
            <span className="text-[10px] font-black text-primary uppercase bg-primary/10 px-2 py-1 rounded">Live</span>
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics.historical_latency}>
                <defs>
                  <linearGradient id="colorLat" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#7c3aed" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{fill: '#666', fontSize: 10}} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#666', fontSize: 10}} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#111', border: '1px solid #ffffff10', borderRadius: '12px' }}
                  itemStyle={{ color: '#7c3aed', fontWeight: 'bold' }}
                />
                <Area type="monotone" dataKey="latency" stroke="#7c3aed" strokeWidth={3} fillOpacity={1} fill="url(#colorLat)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Throughput Chart */}
        <div className="glass-card p-8 rounded-[3rem] border-white/5 bg-white/5 space-y-6">
          <div className="flex items-center justify-between">
             <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-400/20 rounded-xl text-blue-400">
                <BarChart3 size={18} />
              </div>
              <h3 className="font-bold text-xl tracking-tight">Rules Throughput</h3>
            </div>
            <TrendingUp size={18} className="text-blue-400 opacity-50" />
          </div>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics.historical_throughput}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{fill: '#666', fontSize: 10}} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#666', fontSize: 10}} />
                <Tooltip 
                   cursor={{fill: '#ffffff05'}}
                   contentStyle={{ backgroundColor: '#111', border: '1px solid #ffffff10', borderRadius: '12px' }}
                />
                <Bar dataKey="requests" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Decision Pie Chart */}
        <div className="glass-card p-10 rounded-[3rem] border-white/5 bg-white/5 flex flex-col items-center justify-center space-y-6">
          <h3 className="font-bold text-xl tracking-tight self-start">Decision Distribution</h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={decisionData.length ? decisionData : [{name: 'Idle', value: 1}]}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {(decisionData.length ? decisionData : [{name: 'Idle', value: 1}]).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={decisionData.length ? COLORS[index % COLORS.length] : '#111'} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex gap-6 mt-4">
             {decisionData.map((d, i) => (
               <div key={i} className="flex items-center gap-2">
                 <div className="w-2 h-2 rounded-full" style={{backgroundColor: COLORS[i % COLORS.length]}} />
                 <span className="text-[10px] font-black uppercase text-muted-foreground">{d.name}</span>
               </div>
             ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function cn(...inputs: any[]) {
  return inputs.filter(Boolean).join(" ");
}
