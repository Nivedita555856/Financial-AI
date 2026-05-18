import { MessageSquare, BarChart2, Newspaper, Zap } from 'lucide-react'

const COMPANIES = [
  { ticker: 'AAPL',  name: 'Apple',     color: '#a8b2c0' },
  { ticker: 'MSFT',  name: 'Microsoft', color: '#00a4ef' },
  { ticker: 'GOOGL', name: 'Alphabet',  color: '#4285f4' },
  { ticker: 'AMZN',  name: 'Amazon',    color: '#ff9900' },
  { ticker: 'TSLA',  name: 'Tesla',     color: '#e82127' },
  { ticker: 'NVDA',  name: 'NVIDIA',    color: '#76b900' },
]

const NAV = [
  { id: 'chat',       label: 'AI Chat',          Icon: MessageSquare },
  { id: 'financials', label: 'Financials',        Icon: BarChart2     },
  { id: 'news',       label: 'News Feed',         Icon: Newspaper     },
  { id: 'impact',     label: 'Impact Analysis',   Icon: Zap           },
]

export default function Sidebar({ selectedTicker, setTicker, activeTab, setActiveTab, backendStatus }) {
  const active = COMPANIES.find(c => c.ticker === selectedTicker)

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
          {COMPANIES.map(c => (
            <div
              key={c.ticker}
              className={`company-card ${selectedTicker === c.ticker ? 'active' : ''}`}
              style={{ '--company-color': c.color }}
              onClick={() => setTicker(c.ticker)}
              title={c.name}
            >
              <div className="company-ticker">{c.ticker}</div>
              <div className="company-name-small">{c.name}</div>
            </div>
          ))}
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
            {id === 'chat' && <span className="nav-badge">AI</span>}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="status-row">
          <span className={`status-dot ${backendStatus}`} />
          <span style={{ fontSize: 11 }}>
            {backendStatus === 'online'   ? 'Backend connected'   : ''}
            {backendStatus === 'offline'  ? 'Backend offline'     : ''}
            {backendStatus === 'checking' ? 'Connecting…'         : ''}
          </span>
        </div>
        {active && (
          <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-muted)' }}>
            Viewing:&nbsp;
            <span style={{ color: active.color, fontWeight: 600 }}>{active.ticker}</span>
            &nbsp;—&nbsp;{active.name}
          </div>
        )}
        <div style={{ marginTop: 8, fontSize: 10, color: 'var(--text-muted)' }}>
          Neo4j · Weaviate · Groq LLM
        </div>
      </div>
    </aside>
  )
}
