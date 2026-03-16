import { useState } from 'react'
import { Sidebar } from './components/layout/sidebar'
import { Dashboard } from './components/dashboard'
import { RuleEditor } from './components/rule-editor'
import { RuleList } from './components/rule-list'
import { RuleFlow } from './components/rule-flow'
import { ExecutionPlayground } from './components/execution-playground'
import { Categories } from './components/categories'
import { Analytics } from './components/analytics'


const Settings = () => (
  <div className="space-y-10 max-w-4xl">
    <div>
      <h2 className="text-4xl font-bold tracking-tighter">Engine Settings</h2>
      <p className="text-muted-foreground mt-2">Manage your rule engine configuration and security protocols.</p>
    </div>

    <div className="grid grid-cols-1 gap-6">
      {[
        { title: "AI Generation", description: "Configure the LLM provider and prompt sensitivity.", status: "Active (GPT-4o)", icon: Bot },
        { title: "Persistence Layer", description: "JSON local storage and backup frequency.", status: "Enabled", icon: Database },
        { title: "Security Guardrails", description: "Trust thresholds and auto-rejection rules.", status: "0.6 Threshold", icon: ShieldCheck },
        { title: "Audit Logging", description: "Retention period for execution traces.", status: "30 Days", icon: Clock },
      ].map((item, i) => (
        <div key={i} className="glass-card p-8 rounded-[2.5rem] border-white/5 bg-white/5 flex items-center justify-between group hover:bg-white/[0.08] transition-all">
          <div className="flex items-center gap-6">
            <div className="w-14 h-14 bg-primary/10 rounded-2xl flex items-center justify-center text-primary group-hover:scale-110 transition-transform">
              <item.icon size={28} />
            </div>
            <div>
              <h3 className="text-xl font-bold tracking-tight">{item.title}</h3>
              <p className="text-sm text-muted-foreground mt-0.5">{item.description}</p>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <span className="px-3 py-1 bg-white/5 rounded-full text-[10px] font-black uppercase tracking-widest text-primary/80 border border-white/5">{item.status}</span>
            <button className="text-[10px] font-black uppercase text-muted-foreground hover:text-white transition-colors tracking-tighter">Configure →</button>
          </div>
        </div>
      ))}
    </div>
  </div>
);

import { Bot, ShieldCheck, Clock, Database } from "lucide-react";



function App() {
  const [activeTab, setActiveTab] = useState('dashboard')

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />
      case 'editor':
        return <RuleEditor />
      case 'list':
        return <RuleList />
      case 'flow':
        return <RuleFlow />
      case 'categories':
        return <Categories />
      case 'deployment':
        return <ExecutionPlayground />
      case 'analytics':
        return <Analytics />
      case 'settings':
        return <Settings />

      default:
        return <Dashboard />
    }
  }

  return (
    <div className="flex bg-background min-h-screen text-foreground selection:bg-primary/30">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="flex-1 h-screen overflow-y-auto p-12 ml-72 relative">
        {/* Background blobs for aesthetics */}
        <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-primary/20 blur-[180px] rounded-full -z-10 animate-float" />
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-indigo-500/10 blur-[150px] rounded-full -z-10 animate-float-delayed" />

        
        <div className="max-w-7xl mx-auto space-y-12 animate-in fade-in slide-in-from-bottom-6 duration-1000">
          {renderContent()}
        </div>
      </main>
    </div>
  )
}

export default App
