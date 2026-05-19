import { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const API_URL = import.meta.env.VITE_API_URL || ''

const SENTIMENT_COLOR = { Positive: 'var(--green)', Negative: 'var(--red)', Neutral: 'var(--text-muted)' }
const SENTIMENT_ICON  = { Positive: '▲', Negative: '▼', Neutral: '—' }

const TOOLTIP_STYLE = {
  contentStyle: { background: '#0c1829', border: '1px solid #1a2e4a', borderRadius: 8, color: '#e2eaf6', fontSize: 12 },
}

function PriceCard({ ticker, name, price, change, change_pct, sentiment }) {
  const up = change_pct > 0
  const down = change_pct < 0
  const priceColor = up ? 'var(--green)' : down ? 'var(--red)' : 'var(--text-primary)'
  const sColor = SENTIMENT_COLOR[sentiment?.label] || 'var(--text-muted)'

  return (
    <div className="metric-card" style={{ borderLeft: `3px solid ${priceColor}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 14, color: 'var(--cyan)' }}>{ticker}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{name}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: priceColor }}>
            {price != null ? `$${price}` : '—'}
          </div>
          <div style={{ fontSize: 11, color: priceColor, marginTop: 2 }}>
            {change_pct != null ? `${up ? '+' : ''}${change_pct.toFixed(2)}%` : ''}
          </div>
        </div>
      </div>
      {sentiment && (
        <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Sentiment</span>
          <span style={{ fontSize: 11, color: sColor, fontWeight: 600 }}>
            {SENTIMENT_ICON[sentiment.label]} {sentiment.label}
          </span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 'auto' }}>
            {sentiment.count} articles
          </span>
        </div>
      )}
    </div>
  )
}

export default function MarketPanel({ backendStatus }) {
  const [overview, setOverview] = useState([])
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/api/market-overview`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setOverview(data.overview || [])
      setLastUpdated(new Date())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const sentimentData = overview.map(c => ({
    ticker: c.ticker,
    score:  c.sentiment?.score ?? 0,
    label:  c.sentiment?.label ?? 'Neutral',
  }))

  return (
    <div className="panel">
      <div className="section-header">
        <div>
          <div className="section-title">Market Overview</div>
          {lastUpdated && (
            <div className="section-subtitle">
              Updated {lastUpdated.toLocaleTimeString()} · Prices cached 15 min · News sentiment live
            </div>
          )}
        </div>
        <button className="refresh-btn" onClick={load} disabled={loading}>
          {loading ? '…' : '↺ Refresh'}
        </button>
      </div>

      {backendStatus === 'offline' && (
        <div className="offline-warn">
          <div className="offline-warn-icon">⚠️</div>
          <div>
            <div className="offline-warn-title">Backend offline</div>
            <div className="offline-warn-body">Market data requires the backend.</div>
          </div>
        </div>
      )}

      {error && <div className="error-banner">⚠️ {error}</div>}

      {loading && (
        <div className="loading-center"><div className="spinner" /><span>Fetching prices and sentiment…</span></div>
      )}

      {!loading && overview.length > 0 && (
        <>
          {/* Price + Sentiment cards */}
          <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
            {overview.map(c => (
              <PriceCard key={c.ticker} {...c} />
            ))}
          </div>

          {/* Sentiment bar chart */}
          <div className="chart-card">
            <div className="chart-title">News Sentiment Score</div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={sentimentData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id="sentGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#00e87a" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00e87a" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2e4a" />
                <XAxis dataKey="ticker" tick={{ fill: '#8ba3c4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis domain={[-1, 1]} tick={{ fill: '#8ba3c4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [v.toFixed(3), 'Sentiment']} />
                <Area type="monotone" dataKey="score" stroke="#00e87a" strokeWidth={2}
                      fill="url(#sentGrad)" dot={{ fill: '#00e87a', r: 4 }} />
              </AreaChart>
            </ResponsiveContainer>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
              Score: +1.0 = very positive · 0 = neutral · -1.0 = very negative (VADER analysis)
            </div>
          </div>

          {/* Movers table */}
          <div className="chart-card">
            <div className="chart-title">Top Movers</div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Ticker','Company','Price','Change','% Change','Sentiment'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...overview].sort((a,b) => (Math.abs(b.change_pct||0)) - (Math.abs(a.change_pct||0))).map(c => {
                  const up = c.change_pct > 0; const down = c.change_pct < 0
                  const col = up ? 'var(--green)' : down ? 'var(--red)' : 'var(--text-primary)'
                  return (
                    <tr key={c.ticker} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--cyan)' }}>{c.ticker}</td>
                      <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{c.name}</td>
                      <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: col }}>{c.price != null ? `$${c.price}` : '—'}</td>
                      <td style={{ padding: '10px 12px', color: col }}>{c.change != null ? `${up?'+':''}${c.change}` : '—'}</td>
                      <td style={{ padding: '10px 12px', fontWeight: 600, color: col }}>{c.change_pct != null ? `${up?'+':''}${c.change_pct.toFixed(2)}%` : '—'}</td>
                      <td style={{ padding: '10px 12px' }}>
                        <span style={{ color: SENTIMENT_COLOR[c.sentiment?.label], fontSize: 12 }}>
                          {SENTIMENT_ICON[c.sentiment?.label]} {c.sentiment?.label || '—'}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
