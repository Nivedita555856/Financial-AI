import { useState, useEffect, useCallback } from 'react'
import {
  BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'

const API_URL = import.meta.env.VITE_API_URL || ''

const S_COLOR = { Positive: '#00e87a', Negative: '#ff5555', Neutral: '#4a6080' }
const S_ICON  = { Positive: '▲', Negative: '▼', Neutral: '—' }

const TT = {
  contentStyle: {
    background: '#0c1829', border: '1px solid #1a2e4a',
    borderRadius: 8, color: '#e2eaf6', fontSize: 12,
  },
}

/* ── Pulse badge ──────────────────────────────────────────────────────── */
function PulseBadge({ overview }) {
  const up   = overview.filter(c => c.change_pct > 0).length
  const down = overview.filter(c => c.change_pct < 0).length
  const pos  = overview.filter(c => c.sentiment?.label === 'Positive').length
  const avg  = overview.length
    ? (overview.reduce((s, c) => s + (c.sentiment?.score ?? 0), 0) / overview.length).toFixed(2)
    : 0

  const mood = avg >= 0.05 ? 'Bullish' : avg <= -0.05 ? 'Bearish' : 'Neutral'
  const moodColor = avg >= 0.05 ? '#00e87a' : avg <= -0.05 ? '#ff5555' : '#4a6080'

  return (
    <div style={{
      display: 'flex', gap: 12, flexWrap: 'wrap',
      background: 'var(--bg-card)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-sm)', padding: '12px 18px',
      marginBottom: 20, alignItems: 'center',
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
        Market Pulse
      </div>
      <div style={{ width: 1, height: 20, background: 'var(--border)' }} />
      <span style={{ color: '#00e87a', fontSize: 13, fontWeight: 600 }}>▲ {up} Up</span>
      <span style={{ color: '#ff5555', fontSize: 13, fontWeight: 600 }}>▼ {down} Down</span>
      <div style={{ width: 1, height: 20, background: 'var(--border)' }} />
      <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
        {pos}/{overview.length} positive sentiment
      </span>
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Overall</span>
        <span style={{
          fontWeight: 700, fontSize: 13, color: moodColor,
          background: `${moodColor}18`, border: `1px solid ${moodColor}44`,
          borderRadius: 99, padding: '2px 12px',
        }}>
          {mood}
        </span>
      </div>
    </div>
  )
}

/* ── Price card ───────────────────────────────────────────────────────── */
function PriceCard({ ticker, name, price, change, change_pct, sentiment, onClick, selected }) {
  const up = change_pct > 0, down = change_pct < 0
  const col = up ? '#00e87a' : down ? '#ff5555' : 'var(--text-primary)'
  const sCol = S_COLOR[sentiment?.label] || '#4a6080'

  return (
    <div
      onClick={onClick}
      className="metric-card"
      style={{
        cursor: 'pointer',
        borderLeft: `3px solid ${col}`,
        outline: selected ? `1px solid ${col}` : 'none',
        transition: 'all 0.15s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 13, color: 'var(--cyan)' }}>{ticker}</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>{name}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 17, fontWeight: 700, color: col }}>
            {price != null ? `$${price}` : '—'}
          </div>
          <div style={{ fontSize: 11, color: col, marginTop: 1 }}>
            {change_pct != null ? `${up?'+':''}${change_pct.toFixed(2)}%` : ''}
          </div>
        </div>
      </div>
      <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{
          fontSize: 10, color: sCol, fontWeight: 600,
          background: `${sCol}18`, border: `1px solid ${sCol}33`,
          borderRadius: 99, padding: '1px 8px',
        }}>
          {S_ICON[sentiment?.label]} {sentiment?.label || 'Neutral'}
        </span>
        <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 'auto' }}>
          {sentiment?.count ?? 0} articles
        </span>
      </div>
    </div>
  )
}

/* ── Main component ───────────────────────────────────────────────────── */
export default function MarketPanel({ backendStatus }) {
  const [overview, setOverview]         = useState([])
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState(null)
  const [lastUpdated, setLastUpdated]   = useState(null)
  const [selected, setSelected]         = useState(null)
  const [autoRefresh, setAutoRefresh]   = useState(true)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
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
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(load, 5 * 60 * 1000)
    return () => clearInterval(id)
  }, [autoRefresh, load])

  const changeData = overview.map(c => ({
    ticker: c.ticker,
    change: c.change_pct ?? 0,
    price:  c.price,
  }))

  const sentimentData = overview.map(c => ({
    ticker: c.ticker,
    score:  +(c.sentiment?.score ?? 0).toFixed(3),
    label:  c.sentiment?.label ?? 'Neutral',
  }))

  const selectedData = selected ? overview.find(c => c.ticker === selected) : null

  return (
    <div className="panel">
      {/* Header */}
      <div className="section-header">
        <div>
          <div className="section-title">Market Overview</div>
          <div className="section-subtitle" style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 2 }}>
            {lastUpdated && <span>Updated {lastUpdated.toLocaleTimeString()}</span>}
            <label style={{ display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer', fontSize: 11 }}>
              <input
                type="checkbox" checked={autoRefresh}
                onChange={e => setAutoRefresh(e.target.checked)}
                style={{ accentColor: 'var(--cyan)' }}
              />
              Auto-refresh 5 min
            </label>
          </div>
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
            <div className="offline-warn-body">Market data unavailable.</div>
          </div>
        </div>
      )}

      {error && <div className="error-banner">⚠️ {error}</div>}

      {loading && !overview.length && (
        <div className="loading-center"><div className="spinner" /><span>Fetching market data…</span></div>
      )}

      {!loading && overview.length > 0 && (
        <>
          {/* Pulse */}
          <PulseBadge overview={overview} />

          {/* Price cards */}
          <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(190px, 1fr))', marginBottom: 20 }}>
            {overview.map(c => (
              <PriceCard
                key={c.ticker} {...c}
                selected={selected === c.ticker}
                onClick={() => setSelected(selected === c.ticker ? null : c.ticker)}
              />
            ))}
          </div>

          {/* Selected company detail */}
          {selectedData && (
            <div className="chart-card" style={{ marginBottom: 20, borderColor: 'var(--border-bright)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--cyan)', fontWeight: 700, fontSize: 16 }}>
                    {selectedData.ticker}
                  </span>
                  <span style={{ color: 'var(--text-muted)', fontSize: 13, marginLeft: 10 }}>{selectedData.name}</span>
                </div>
                <button
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16 }}
                  onClick={() => setSelected(null)}
                >✕</button>
              </div>
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                {[
                  ['Price',     selectedData.price != null ? `$${selectedData.price}` : '—'],
                  ['Change',    selectedData.change != null ? `${selectedData.change > 0?'+':''}$${selectedData.change}` : '—'],
                  ['% Change',  selectedData.change_pct != null ? `${selectedData.change_pct > 0?'+':''}${selectedData.change_pct?.toFixed(2)}%` : '—'],
                  ['Prev Close',selectedData.prev_close != null ? `$${selectedData.prev_close}` : '—'],
                  ['Sentiment', selectedData.sentiment?.label || '—'],
                  ['Sent Score',selectedData.sentiment?.score?.toFixed(3) ?? '—'],
                  ['Articles',  selectedData.sentiment?.count ?? '—'],
                ].map(([label, val]) => (
                  <div key={label}>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
                    <div style={{ fontSize: 14, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', marginTop: 3 }}>{val}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Price % Change chart */}
          <div className="chart-card">
            <div className="chart-title">Daily Price Change (%)</div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={changeData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2e4a" vertical={false} />
                <XAxis dataKey="ticker" tick={{ fill: '#8ba3c4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#8ba3c4', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
                <Tooltip {...TT} formatter={(v) => [`${v > 0?'+':''}${v?.toFixed(2)}%`, 'Change']} />
                <ReferenceLine y={0} stroke="#1a2e4a" strokeWidth={1} />
                <Bar dataKey="change" radius={[4, 4, 0, 0]}>
                  {changeData.map((entry, i) => (
                    <Cell key={i} fill={entry.change > 0 ? '#00e87a' : entry.change < 0 ? '#ff5555' : '#4a6080'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Sentiment chart */}
          <div className="chart-card">
            <div className="chart-title">News Sentiment Score (VADER)</div>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={sentimentData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2e4a" vertical={false} />
                <XAxis dataKey="ticker" tick={{ fill: '#8ba3c4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis domain={[-1, 1]} tick={{ fill: '#8ba3c4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip {...TT} formatter={(v) => [v, 'Sentiment score']} />
                <ReferenceLine y={0} stroke="#1a2e4a" />
                <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                  {sentimentData.map((entry, i) => (
                    <Cell key={i} fill={entry.score >= 0.05 ? '#00e87a' : entry.score <= -0.05 ? '#ff5555' : '#4a6080'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
              +1.0 very positive · 0 neutral · -1.0 very negative
            </div>
          </div>

          {/* Top movers table */}
          <div className="chart-card">
            <div className="chart-title">Top Movers</div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Rank','Ticker','Price','Change','% Change','Sentiment','Score'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontSize: 10, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...overview]
                  .sort((a,b) => Math.abs(b.change_pct||0) - Math.abs(a.change_pct||0))
                  .map((c, i) => {
                    const up = c.change_pct > 0, down = c.change_pct < 0
                    const col = up ? '#00e87a' : down ? '#ff5555' : 'var(--text-primary)'
                    const sCol = S_COLOR[c.sentiment?.label] || '#4a6080'
                    return (
                      <tr
                        key={c.ticker}
                        style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer', background: selected === c.ticker ? 'var(--bg-card-alt)' : 'transparent' }}
                        onClick={() => setSelected(selected === c.ticker ? null : c.ticker)}
                      >
                        <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 11 }}>#{i+1}</td>
                        <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--cyan)' }}>{c.ticker}</td>
                        <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: col }}>{c.price != null ? `$${c.price}` : '—'}</td>
                        <td style={{ padding: '10px 12px', color: col }}>{c.change != null ? `${up?'+':''}$${c.change}` : '—'}</td>
                        <td style={{ padding: '10px 12px', fontWeight: 700, color: col }}>{c.change_pct != null ? `${up?'+':''}${c.change_pct.toFixed(2)}%` : '—'}</td>
                        <td style={{ padding: '10px 12px' }}>
                          <span style={{ color: sCol, fontSize: 12, fontWeight: 600 }}>
                            {S_ICON[c.sentiment?.label]} {c.sentiment?.label || '—'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontSize: 11, color: sCol }}>
                          {c.sentiment?.score?.toFixed(3) ?? '—'}
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
