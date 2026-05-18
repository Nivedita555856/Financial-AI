import { useState, useEffect } from 'react'

const TAB_LABELS = {
  chat: 'AI Chat',
  financials: 'Financials',
  news: 'News Feed',
  impact: 'Impact Analysis',
}

export default function TopBar({ ticker, tab, backendStatus, onWakeUp }) {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const timeStr = time.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <div className="topbar">
      <div className="topbar-left">
        <span className="topbar-ticker">{ticker}</span>
        <span className="topbar-slash">/</span>
        <span className="topbar-tab">{TAB_LABELS[tab] || tab}</span>
      </div>
      <div className="topbar-right">
        <span className="topbar-clock">{timeStr}</span>
        <div className="topbar-status">
          <span className={`status-dot ${backendStatus}`} />
          {backendStatus === 'online'   && 'Connected'}
          {backendStatus === 'offline'  && 'Backend offline'}
          {backendStatus === 'checking' && 'Connecting…'}
        </div>
        {backendStatus === 'offline' && (
          <button className="wake-btn" onClick={onWakeUp} style={{ margin: 0, padding: '5px 10px' }}>
            Retry ↺
          </button>
        )}
      </div>
    </div>
  )
}
