import { useState } from 'react'
import { analyzeImpact } from '../api/client'
import { Zap } from 'lucide-react'

const COMPANIES = [
  { ticker: 'AAPL',  name: 'Apple' },
  { ticker: 'MSFT',  name: 'Microsoft' },
  { ticker: 'GOOGL', name: 'Alphabet' },
  { ticker: 'AMZN',  name: 'Amazon' },
  { ticker: 'TSLA',  name: 'Tesla' },
  { ticker: 'NVDA',  name: 'NVIDIA' },
]

const EXAMPLE_ISSUES = [
  'supply chain disruption in Asia',
  'antitrust investigation by EU',
  'sharp rise in interest rates',
  'AI regulatory crackdown',
  'chip export ban to China',
  'major data breach incident',
]

export default function ImpactPanel({ ticker, backendStatus }) {
  const [selectedTicker, setSelectedTicker] = useState(ticker)
  const [issue, setIssue]                   = useState('')
  const [loading, setLoading]               = useState(false)
  const [result, setResult]                 = useState(null)
  const [error, setError]                   = useState(null)

  // Sync with parent ticker when it changes
  useState(() => { setSelectedTicker(ticker) }, [ticker])

  async function analyze() {
    if (!issue.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await analyzeImpact(selectedTicker, issue.trim())
      setResult(data.analysis || data.error || 'No analysis returned.')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <div className="section-header">
        <div>
          <div className="section-title">Impact Analysis</div>
        </div>
      </div>

      {backendStatus === 'offline' && (
        <div className="offline-warn">
          <div className="offline-warn-icon">⚠️</div>
          <div>
            <div className="offline-warn-title">Backend offline</div>
            <div className="offline-warn-body">
              Analysis requires the FastAPI backend. On Render free tier, it may take ~30s to wake up on first request.
            </div>
          </div>
        </div>
      )}

      {/* Form */}
      <div className="impact-form-card">
        <div className="impact-form-title">Configure Analysis</div>

        <div className="form-grid">
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

          <button className="analyze-btn" onClick={analyze} disabled={loading || !issue.trim()}>
            {loading ? 'Analyzing…' : <><Zap size={14} style={{ marginRight: 6 }} />Analyze</>}
          </button>
        </div>

        {/* Example issues */}
        <div style={{ marginTop: 16 }}>
          <div className="form-label" style={{ marginBottom: 8 }}>Try an example</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {EXAMPLE_ISSUES.map(ex => (
              <button
                key={ex}
                className="chip"
                onClick={() => { setIssue(ex); }}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="loading-center">
          <div className="spinner" />
          <span>Querying Neo4j graph and Groq LLM…</span>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* Result */}
      {result && !loading && (
        <div className="impact-result">
          <div className="impact-result-header">
            <span className="impact-badge">⚡ Impact Analysis</span>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              {selectedTicker} — {issue}
            </span>
          </div>
          <div className="impact-text">{result}</div>
        </div>
      )}

      {/* Empty prompt */}
      {!result && !loading && !error && (
        <div className="empty-state">
          <div className="empty-icon">⚡</div>
          <h3>Ready to analyze</h3>
          <p>Select a company, describe an issue, and hit Analyze.</p>
        </div>
      )}
    </div>
  )
}
