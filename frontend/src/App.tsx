import { useState } from 'react'
import { Sidebar } from './components/layout/sidebar'
import { Dashboard } from './components/dashboard'
import { RuleEditor } from './components/rule-editor'
import { RuleList } from './components/rule-list'
import { RuleFlow } from './components/rule-flow'
import { ExecutionPlayground } from './components/execution-playground'
import { Categories } from './components/categories'

// Placeholder for remaining components
const Analytics = () => (
  <div className="glass-card p-10 rounded-[2.5rem] border-white/5 bg-white/5">
    <h2 className="text-3xl font-bold mb-4">Analytics & Reports</h2>
    <p className="text-muted-foreground italic">Real-time performance metrics... coming soon.</p>
  </div>
);

const Settings = () => (
  <div className="glass-card p-10 rounded-[2.5rem] border-white/5 bg-white/5">
    <h2 className="text-3xl font-bold mb-4">Engine Settings</h2>
    <p className="text-muted-foreground italic">Configuration and security... coming soon.</p>
  </div>
);

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
      case 'playground':
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
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary/20 blur-[150px] rounded-full -z-10 animate-pulse" />
        <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-500/10 blur-[120px] rounded-full -z-10" />
        
        <div className="max-w-7xl mx-auto space-y-12 animate-in fade-in slide-in-from-bottom-6 duration-1000">
          {renderContent()}
        </div>
      </main>
    </div>
  )
}

export default App
