import { useState, useEffect, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import ChatPanel from './components/ChatPanel'
import FinancialsPanel from './components/FinancialsPanel'
import NewsPanel from './components/NewsPanel'
import ImpactPanel from './components/ImpactPanel'
import { checkHealth } from './api/client'

const TABS = ['chat', 'financials', 'news', 'impact']

export default function App() {
  const [activeTab, setActiveTab]       = useState('chat')
  const [selectedTicker, setTicker]     = useState('AAPL')
  const [backendStatus, setBackendStatus] = useState('checking')
  // Re-poll health every 30 s
  const poll = useCallback(async () => {
    const data = await checkHealth()
    setBackendStatus(data.status === 'healthy' ? 'online' : 'offline')
  }, [])

  useEffect(() => {
    poll()
    const id = setInterval(poll, 30_000)
    return () => clearInterval(id)
  }, [poll])

  return (
    <div className="app-layout">
      <Sidebar
        selectedTicker={selectedTicker}
        setTicker={setTicker}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        backendStatus={backendStatus}
      />
      <div className="main-content">
        <TopBar
          ticker={selectedTicker}
          tab={activeTab}
          backendStatus={backendStatus}
          onWakeUp={poll}
        />
        <div className="panel-area">
          {activeTab === 'chat'       && <ChatPanel      ticker={selectedTicker} backendStatus={backendStatus} />}
          {activeTab === 'financials' && <FinancialsPanel ticker={selectedTicker} backendStatus={backendStatus} />}
          {activeTab === 'news'       && <NewsPanel       ticker={selectedTicker} backendStatus={backendStatus} />}
          {activeTab === 'impact'     && <ImpactPanel     ticker={selectedTicker} backendStatus={backendStatus} />}
        </div>
      </div>
    </div>
  )
}
