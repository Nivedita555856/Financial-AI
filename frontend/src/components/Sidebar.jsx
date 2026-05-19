import { useEffect, useState } from 'react'
import { MessageSquare, BarChart2, Newspaper, Zap, TrendingUp } from 'lucide-react'

const COMPANIES = [
  { ticker: 'AAPL',  name: 'Apple',     color: '#a8b2c0' },
  { ticker: 'MSFT',  name: 'Microsoft', color: '#00a4ef' },
  { ticker: 'GOOGL', name: 'Alphabet',  color: '#4285f4' },
  { ticker: 'AMZN',  name: 'Amazon',    color: '#ff9900' },
  { ticker: 'TSLA',  name: 'Tesla',     color: '#e82127' },
  { ticker: 'NVDA',  name: 'NVIDIA',    color: '#76b900' },
]

const NAV = [
  { id: 'chat',      label: 'AI Chat',          Icon: MessageSquare },
  { id: 'market',    label: 'Market Overview',   Icon: TrendingUp    },
  { id: 'financials',label: 'Financials',        Icon: BarChart2     },
  { id: 'news',      label: 'News Feed',         Icon: Newspaper     },
  { id: 'impact',    label: 'Impact Analysis',   Icon: Zap           },
]

const API_URL = import.meta.env.VITE_API_URL || ''

export default function Sidebar({ selectedTicker, setTicker, activeTab, setActiveTab, backendStatus }) {
  const [prices, setPrices] = useState({})

  useEffect(() => {
    fetchPrices()
    const id = setInterval(fetchPrices, 15 * 60 * 1000) // every 15 min
    return () => clearInterval(id)
  }, [])

  async function fetchPrices() {
    try {
      const res = await fetch(`${API_URL}/api/prices`)
      if (res.ok) {
        const data = await res.json()
        setPrices(data.prices || {})
      }
    } catch {}
  }

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-logo">
        <div className="brand">
          <div className="brand-icon">📈</div>
          <div>
            <div className="brand-name">Financial Insights</div>
            <div className="brand-sub">Graph RAG Copilot</div>
          </div>
        </div>
      </div>

      {/* Company selector */}
      <div className="sidebar-companies">
        <div className="sidebar-section-title">Companies</div>
        <div className="company-grid">
          {COMPANIES.map(c => {
            const p = prices[c.ticker]
            const up = p?.change_pct > 0
            const down = p?.change_pct < 0
            return (
              <div
                key={c.ticker}
                className={`company-card ${selectedTicker === c.ticker ? 'active' : ''}`}
                style={{ '--company-color': c.color }}
                onClick={() => setTicker(c.ticker)}
              >
                <div className="company-ticker">{c.ticker}</div>
                {p?.price ? (
                  <>
                    <div style={{ fontSize: 11, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                      ${p.price}
                    </div>
                    <div style={{ fontSize: 10, color: up ? 'var(--green)' : down ? 'var(--red)' : 'var(--text-muted)', marginTop: 1 }}>
                      {up ? '▲' : down ? '▼' : '—'} {p.change_pct != null ? Math.abs(p.change_pct).toFixed(2) + '%' : ''}
                    </div>
                  </>
                ) : (
                  <div className="company-name-small">{c.name}</div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="sidebar-section-title" style={{ marginBottom: 8 }}>Navigation</div>
        {NAV.map(({ id, label, Icon }) => (
          <div
            key={id}
            className={`nav-item ${activeTab === id ? 'active' : ''}`}
            onClick={() => setActiveTab(id)}
          >
            <Icon size={16} />
            <span>{label}</span>
            {id === 'chat'   && <span className="nav-badge">AI</span>}
            {id === 'market' && <span className="nav-badge">Live</span>}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="status-row">
          <span className={`status-dot ${backendStatus}`} />
          <span style={{ fontSize: 11 }}>
            {backendStatus === 'online'   ? 'Backend connected' : ''}
            {backendStatus === 'offline'  ? 'Backend offline'   : ''}
            {backendStatus === 'checking' ? 'Connecting…'       : ''}
          </span>
        </div>
        <div style={{ marginTop: 8, fontSize: 10, color: 'var(--text-muted)' }}>
          Neo4j · Weaviate · Groq · GDELT
        </div>
      </div>
    </aside>
  )
}
