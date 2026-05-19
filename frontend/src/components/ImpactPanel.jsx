import { useState, useEffect } from 'react'
import { analyzeImpact, getRelationships } from '../api/client'
import { Zap } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || ''

const COMPANIES = [
  { ticker: 'AAPL',  name: 'Apple',     color: '#a8b2c0' },
  { ticker: 'MSFT',  name: 'Microsoft', color: '#00a4ef' },
  { ticker: 'GOOGL', name: 'Alphabet',  color: '#4285f4' },
  { ticker: 'AMZN',  name: 'Amazon',    color: '#ff9900' },
  { ticker: 'TSLA',  name: 'Tesla',     color: '#e82127' },
  { ticker: 'NVDA',  name: 'NVIDIA',    color: '#76b900' },
]

const EXAMPLE_ISSUES = [
  'supply chain disruption in Asia',
  'antitrust investigation by EU',
  'sharp rise in interest rates',
  'AI regulatory crackdown',
  'chip export ban to China',
  'major data breach incident',
  'earnings miss this quarter',
  'key executive resignation',
]

const REL_COLORS = {
  suppliers:   { color: '#ff9900', label: 'Suppliers',   icon: '📦', impact: 'Revenue decline risk' },
  customers:   { color: '#00d4ff', label: 'Customers',   icon: '🛒', impact: 'Cost increase risk' },
  competitors: { color: '#ff5555', label: 'Competitors', icon: '⚔️',  impact: 'Market share opportunity' },
  partners:    { color: '#a78bfa', label: 'Partners',    icon: '🤝', impact: 'Partnership risk' },
}

/* ── Ripple Effect Visualization ──────────────────────────────────────── */
function RippleEffect({ ticker, relationships, issue }) {
  const company = COMPANIES.find(c => c.ticker === ticker)
  const hasAny = Object.values(relationships).some(arr => arr?.length > 0)
  if (!hasAny) return null

  return (
    <div className="chart-card" style={{ marginBottom: 20 }}>
      <div className="chart-title" style={{ marginBottom: 16 }}>
        Ripple Effect — {ticker} impacted by "{issue}"
      </div>

      {/* Center company */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <div style={{
            background: `${company?.color || '#00d4ff'}22`,
            border: `2px solid ${company?.color || '#00d4ff'}`,
            borderRadius: 12, padding: '10px 24px',
            textAlign: 'center', minWidth: 120,
          }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 16, color: company?.color || 'var(--cyan)' }}>
              {ticker}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>PRIMARY</div>
          </div>
        </div>

        {/* Relationship rows */}
        {Object.entries(REL_COLORS).map(([key, meta]) => {
          const items = relationships[key] || []
          if (!items.length) return null
          return (
            <div key={key}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ height: 1, flex: 1, background: `${meta.color}44` }} />
                <span style={{
                  fontSize: 10, fontWeight: 600, color: meta.color,
                  textTransform: 'uppercase', letterSpacing: '0.08em',
                }}>
                  {meta.icon} {meta.label} — {meta.impact}
                </span>
                <div style={{ height: 1, flex: 1, background: `${meta.color}44` }} />
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                {items.map(rel => (
                  <div key={rel} style={{
                    background: `${meta.color}12`,
                    border: `1px solid ${meta.color}44`,
                    borderRadius: 8, padding: '6px 14px',
                    fontSize: 12, color: meta.color,
                    fontFamily: 'var(--font-mono)', fontWeight: 600,
                  }}>
                    {rel}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ── Analysis result display ──────────────────────────────────────────── */
function AnalysisResult({ result, ticker, issue }) {
  return (
    <div className="impact-result">
      <div className="impact-result-header" style={{ marginBottom: 16 }}>
        <span className="impact-badge">⚡ Impact Analysis</span>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          {ticker} — {issue}
        </span>
      </div>
      <div className="impact-text">{result}</div>
    </div>
  )
}

/* ── Main component ───────────────────────────────────────────────────── */
export default function ImpactPanel({ ticker, backendStatus }) {
  const [selectedTicker, setSelectedTicker] = useState(ticker)
  const [issue, setIssue]                   = useState('')
  const [loading, setLoading]               = useState(false)
  const [result, setResult]                 = useState(null)
  const [relationships, setRelationships]   = useState(null)
  const [error, setError]                   = useState(null)
  const [history, setHistory]               = useState([])

  useEffect(() => { setSelectedTicker(ticker) }, [ticker])

  async function analyze() {
    if (!issue.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    setRelationships(null)

    try {
      // Fetch LLM analysis + relationships in parallel
      const [impactRes, relRes] = await Promise.all([
        analyzeImpact(selectedTicker, issue.trim()),
        getRelationships(selectedTicker).catch(() => null),
      ])

      const analysis = impactRes.analysis || impactRes.error || 'No analysis returned.'
      setResult(analysis)

      if (relRes) {
        setRelationships({
          suppliers:   relRes.suppliers   || [],
          customers:   relRes.customers   || [],
          competitors: relRes.competitors || [],
          partners:    relRes.partners    || [],
        })
      }

      // Save to history
      setHistory(prev => [
        { ticker: selectedTicker, issue: issue.trim(), result: analysis, time: new Date() },
        ...prev.slice(0, 4),
      ])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <div className="section-title" style={{ marginBottom: 20 }}>Impact Analysis</div>

      {backendStatus === 'offline' && (
        <div className="offline-warn">
          <div className="offline-warn-icon">⚠️</div>
          <div>
            <div className="offline-warn-title">Backend offline</div>
            <div className="offline-warn-body">First request on Render free tier takes ~30s to wake up.</div>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>

        {/* Left: form + result */}
        <div>
          {/* Form */}
          <div className="impact-form-card" style={{ marginBottom: 20 }}>
            <div className="impact-form-title" style={{ marginBottom: 16 }}>Configure</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Company</label>
                <select
                  className="form-select"
                  value={selectedTicker}
                  onChange={e => setSelectedTicker(e.target.value)}
                >
                  {COMPANIES.map(c => (
                    <option key={c.ticker} value={c.ticker}>{c.ticker} — {c.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Issue / Scenario</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. supply chain disruption in Asia"
                  value={issue}
                  onChange={e => setIssue(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && analyze()}
                />
              </div>
              <button
                className="analyze-btn"
                onClick={analyze}
                disabled={loading || !issue.trim()}
                style={{ alignSelf: 'flex-start' }}
              >
                {loading
                  ? 'Analyzing…'
                  : <><Zap size={14} style={{ marginRight: 6, display: 'inline' }} />Analyze Impact</>
                }
              </button>
            </div>

            <div style={{ marginTop: 16 }}>
              <div className="form-label" style={{ marginBottom: 8 }}>Examples</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {EXAMPLE_ISSUES.map(ex => (
                  <button key={ex} className="chip" onClick={() => setIssue(ex)}>{ex}</button>
                ))}
              </div>
            </div>
          </div>

          {/* Loading */}
          {loading && (
            <div className="loading-center">
              <div className="spinner" />
              <span>Querying graph + Groq LLM…</span>
            </div>
          )}

          {/* Error */}
          {error && !loading && <div className="error-banner">⚠️ {error}</div>}

          {/* Ripple visualization */}
          {relationships && result && !loading && (
            <RippleEffect ticker={selectedTicker} relationships={relationships} issue={issue} />
          )}

          {/* LLM Result */}
          {result && !loading && (
            <AnalysisResult result={result} ticker={selectedTicker} issue={issue} />
          )}

          {!result && !loading && !error && (
            <div className="empty-state">
              <div className="empty-icon">⚡</div>
              <h3>Ready to analyze</h3>
              <p>Select a company, describe an issue, and hit Analyze.</p>
            </div>
          )}
        </div>

        {/* Right: history panel */}
        <div>
          {/* Relationship summary for selected ticker */}
          <RelationshipSummary ticker={selectedTicker} />

          {/* History */}
          {history.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10 }}>
                Recent analyses
              </div>
              {history.map((h, i) => (
                <div
                  key={i}
                  className="card-sm"
                  style={{ marginBottom: 8, cursor: 'pointer' }}
                  onClick={() => {
                    setSelectedTicker(h.ticker)
                    setIssue(h.issue)
                    setResult(h.result)
                  }}
                >
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--cyan)', fontWeight: 700 }}>
                    {h.ticker}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 3, lineHeight: 1.4 }}>
                    {h.issue}
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                    {h.time.toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── Relationship summary sidebar widget ──────────────────────────────── */
function RelationshipSummary({ ticker }) {
  const [data, setData]   = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setData(null)
    setLoading(true)
    getRelationships(ticker)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [ticker])

  return (
    <div className="card-sm">
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10 }}>
        {ticker} Relationships
      </div>
      {loading && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Loading…</div>}
      {data && Object.entries(REL_COLORS).map(([key, meta]) => {
        const items = data[key] || []
        return (
          <div key={key} style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 10, color: meta.color, fontWeight: 600, marginBottom: 4 }}>
              {meta.icon} {meta.label} ({items.length})
            </div>
            {items.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {items.map(t => (
                  <span key={t} style={{
                    fontSize: 10, color: meta.color,
                    background: `${meta.color}18`, border: `1px solid ${meta.color}33`,
                    borderRadius: 99, padding: '1px 7px',
                    fontFamily: 'var(--font-mono)', fontWeight: 600,
                  }}>{t}</span>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>None</div>
            )}
          </div>
        )
      })}
    </div>
  )
}
