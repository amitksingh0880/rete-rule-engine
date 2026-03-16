import { useEffect, useState, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import axios from "axios";
import { 
  RefreshCw, 
  Play, 
  Zap, 
  Info, 
  ChevronRight,
  Database
} from "lucide-react";
import { cn } from "@/lib/utils";

// --- Custom Node Types ---

// --- Custom Node Types ---

const StartNode = ({ data }: any) => (
  <div className="px-6 py-4 glass-card rounded-[2rem] border-green-500/30 bg-green-500/10 shadow-[0_0_40px_RGBA(34,197,94,0.15)] min-w-[180px] relative group hover:scale-105 transition-all duration-500">
    <div className="flex items-center gap-4">
      <div className="p-3 bg-green-500/20 rounded-2xl text-green-400 group-hover:bg-green-500 group-hover:text-white transition-all shadow-lg shadow-green-500/20">
        <Database size={22} />
      </div>
      <div>
        <p className="text-[10px] font-black uppercase text-green-500/60 tracking-widest mb-0.5">Input Fact</p>
        <p className="text-base font-black text-white tracking-tight">{data.label}</p>
      </div>
    </div>
    <Handle type="source" position={Position.Right} className="!w-4 !h-4 !bg-green-500 !border-4 !border-white/20 !-right-2 shadow-xl" />
  </div>
);

const RuleNode = ({ data }: any) => (
  <div className={cn(
    "px-6 py-5 glass-card rounded-[2rem] border-white/10 bg-white/5 min-w-[220px] transition-all duration-700 relative group overflow-hidden",
    data.isActive ? "border-primary/60 bg-primary/20 shadow-[0_0_50px_RGBA(124,58,237,0.3)] scale-110 ring-4 ring-primary/20 z-10" : "hover:bg-white/10 hover:border-white/20"
  )}>
    {data.isActive && (
      <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent animate-pulse" />
    )}
    <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-white/20 !border-none !-left-1.5" />
    <div className="flex items-center gap-4 relative z-10">
      <div className={cn(
        "p-3 rounded-2xl transition-all duration-500 shadow-lg",
        data.isActive ? "bg-primary text-white shadow-primary/40 scale-110" : "bg-white/5 text-muted-foreground group-hover:text-white"
      )}>
        <Zap size={22} fill={data.isActive ? "currentColor" : "none"} />
      </div>
      <div>
        <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest mb-0.5">Condition</p>
        <p className="text-base font-black text-white tracking-tighter">{data.label}</p>
      </div>
    </div>
    {data.isActive && (
       <div className="absolute top-3 right-3 px-3 py-1 bg-primary text-[9px] font-black text-white rounded-full uppercase tracking-widest shadow-xl animate-in fade-in zoom-in duration-300">
         Matched
       </div>
    )}
    <Handle type="source" position={Position.Right} className="!w-3 !h-3 !bg-white/20 !border-none !-right-1.5" />
  </div>
);

const TerminalNode = ({ data }: any) => (
  <div className={cn(
    "px-8 py-6 glass-card rounded-[2.5rem] border-indigo-500/30 bg-indigo-500/10 min-w-[200px] transition-all duration-1000 relative group",
    data.isActive ? "border-indigo-400 bg-indigo-500/30 shadow-[0_0_60px_RGBA(99,102,241,0.4)] ring-4 ring-indigo-500/30 scale-110" : "opacity-60 grayscale hover:opacity-100 hover:grayscale-0"
  )}>
    <Handle type="target" position={Position.Left} className="!w-5 !h-5 !bg-indigo-500 !border-4 !border-white/20 !-left-2.5 shadow-xl" />
    <div className="flex items-center gap-4">
      <div className={cn(
        "p-4 rounded-[1.5rem] shadow-2xl transition-all duration-500",
        data.isActive ? "bg-indigo-500 text-white rotate-3" : "bg-indigo-500/20 text-indigo-400"
      )}>
        <Play size={24} fill={data.isActive ? "currentColor" : "none"} />
      </div>
      <div>
        <p className="text-[10px] font-black uppercase text-indigo-500/50 tracking-widest mb-0.5">Execution Result</p>
        <p className="text-lg font-black text-white tracking-tighter">{data.label}</p>
      </div>
    </div>
  </div>
);


const nodeTypes = {
  alpha: StartNode,
  beta: RuleNode,
  terminal: TerminalNode,
};

// --- Main Component ---

export function RuleFlow() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [traceData, setTraceData] = useState<any>(null);
  const [dryRunLoading, setDryRunLoading] = useState(false);

  const fetchGraph = useCallback(async (activeNodes: string[] = []) => {
    setLoading(true);
    try {
      const res = await axios.get("http://localhost:8000/network");
      
      const flowNodes = res.data.nodes.map((node: any, idx: number) => {
        const isActive = activeNodes.includes(node.id);
        return {
          id: node.id,
          type: node.type, // Custom types
          data: { 
            label: node.label, 
            isActive,
            ...node.data 
          },
          // Fixed positions for now to avoid jumpiness during refresh
          position: { x: (idx % 6) * 300, y: Math.floor(idx / 6) * 200 },
        };
      });

      const flowEdges = res.data.edges.map((edge: any) => {
        const isHot = activeNodes.includes(edge.source) && activeNodes.includes(edge.target);
        return {
          ...edge,
          animated: isHot,
          label: edge.label || (isHot ? "PASS" : ""),
          labelStyle: { fill: isHot ? "#a855f7" : "#555", fontWeight: 700, fontSize: 10 },
          style: { 
            stroke: isHot ? "#a855f7" : "rgba(255,255,255,0.1)", 
            strokeWidth: isHot ? 3 : 1 
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isHot ? "#a855f7" : "rgba(255,255,255,0.1)",
          },
        };
      });

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (err) {
      console.error("Failed to fetch rule network", err);
    } finally {
      setLoading(false);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const handleDryRun = async () => {
    setDryRunLoading(true);
    try {
      // Mock fact for dry run - in a real app, this would come from a modal or panel
      const facts = [{ fact_type: "Applicant", attributes: { score: 750, income: 60000 } }];
      const res = await axios.post("http://localhost:8000/execute", { facts, trace: true });
      
      // In a real Rete network, we'd need node IDs in the trace. 
      // For this mock, we'll just activate nodes that match the labels or types.
      // Since our ReteNetwork.export_graph includes IDs, we can use those.
      const activeIds = res.data.matched_rules; // Rules are terminal nodes
      
      // Highlight the path (Mock activation)
      fetchGraph(activeIds);
      setTraceData(res.data);
    } catch (err) {
      console.error("Dry run failed", err);
    } finally {
      setDryRunLoading(false);
    }
  };

  return (
    <div className="space-y-6 h-[calc(100vh-160px)] flex flex-col relative">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h2 className="text-4xl font-bold tracking-tighter">Network Topology</h2>
          <p className="text-muted-foreground font-medium">Visualization of compiled Rete nodes and logical paths.</p>
        </div>
        <div className="flex gap-4">
          <button 
            onClick={handleDryRun}
            disabled={dryRunLoading}
            className="flex items-center gap-2 px-6 py-3 bg-primary text-white rounded-2xl font-bold uppercase tracking-tighter shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 transition-all text-xs"
          >
            {dryRunLoading ? <RefreshCw className="animate-spin" size={16} /> : <Play fill="currentColor" size={16} />}
            Run Live Simulation
          </button>
          <button 
            onClick={() => fetchGraph()}
            className="flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/5 rounded-2xl text-xs font-bold uppercase tracking-tighter hover:bg-white/10 transition-all text-white/70"
          >
            <RefreshCw size={16} className={loading && !dryRunLoading ? "animate-spin" : ""} />
            Reset State
          </button>
        </div>
      </div>

      <div className="flex-1 glass-card rounded-[2.5rem] overflow-hidden border border-white/5 shadow-2xl relative bg-black/40">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          colorMode="dark"
        >
          <Background color="#111" gap={30} size={1} />
          <Controls className="!bg-black/50 !border-white/5 !rounded-xl overflow-hidden" />
          <MiniMap 
            nodeColor={(n: any) => {
              if (n.type === 'alpha') return '#22c55e';
              if (n.type === 'terminal') return '#a855f7';
              return '#444';
            }}
            maskColor="rgba(0,0,0,0.7)"
            className="!bg-black/50 !border-white/5 !rounded-2xl"
          />
        </ReactFlow>

        {/* Floating Attribution Panel */}
        <div className="absolute top-6 right-6 w-72 glass-card p-6 rounded-3xl border border-white/5 bg-black/60 backdrop-blur-xl z-10 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-[10px] font-black uppercase text-muted-foreground tracking-[0.2em]">Network Stats</h4>
            <Info size={14} className="text-primary" />
          </div>
          <div className="space-y-3">
             <div className="flex items-center justify-between">
               <span className="text-xs text-white/60">Alpha Nodes</span>
               <span className="text-xs font-mono font-bold text-green-400">{(nodes as any[]).filter(n => n.id.startsWith('alpha')).length}</span>
             </div>
             <div className="flex items-center justify-between">
               <span className="text-xs text-white/60">Beta Nodes</span>
               <span className="text-xs font-mono font-bold text-primary">{(nodes as any[]).filter(n => n.id.startsWith('beta')).length}</span>
             </div>
             <div className="flex items-center justify-between">
               <span className="text-xs text-white/60">Total Edges</span>
               <span className="text-xs font-mono font-bold text-white">{edges.length}</span>
             </div>
          </div>
          {traceData && (
            <div className="pt-4 border-t border-white/5 animate-in slide-in-from-top-2">
               <p className="text-[10px] font-black text-primary uppercase mb-2">Simulation Result</p>
               <div className="flex items-center justify-between px-3 py-2 bg-primary/10 rounded-xl border border-primary/20">
                 <span className="text-[10px] font-bold text-white">{traceData.decision}</span>
                 <ChevronRight size={10} className="text-primary" />
               </div>
            </div>
          )}
        </div>

        {(loading || dryRunLoading) && (
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
               <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin" />
               <p className="text-xs font-black uppercase tracking-[0.3em] text-primary animate-pulse">Syncing Network Topology</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
