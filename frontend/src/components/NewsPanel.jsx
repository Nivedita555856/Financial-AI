import { useState, useEffect } from 'react'
import { getNews } from '../api/client'

const COMPANY_NAMES = {
  AAPL: 'Apple', MSFT: 'Microsoft', GOOGL: 'Alphabet',
  AMZN: 'Amazon', TSLA: 'Tesla', NVDA: 'NVIDIA',
}

function formatTimestamp(ts) {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    if (isNaN(d)) return ts
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
  } catch {
    return ts
  }
}

export default function NewsPanel({ ticker, backendStatus }) {
  const [news, setNews]       = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  useEffect(() => {
    loadNews()
  }, [ticker])

  async function loadNews() {
    setLoading(true)
    setError(null)
    try {
      const res = await getNews(ticker, 10)
      setNews(res.news || [])
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
          <div className="section-title">{COMPANY_NAMES[ticker] || ticker} — News</div>
        </div>
        <button className="refresh-btn" onClick={loadNews} disabled={loading}>
          {loading ? '…' : '↺ Refresh'}
        </button>
      </div>

      {backendStatus === 'offline' && (
        <div className="offline-warn">
          <div className="offline-warn-icon">⚠️</div>
          <div>
            <div className="offline-warn-title">Backend offline</div>
            <div className="offline-warn-body">News cannot be fetched until the backend wakes up.</div>
          </div>
        </div>
      )}

      {loading && (
        <div className="loading-center">
          <div className="spinner" />
          <span>Searching Weaviate vector store…</span>
        </div>
      )}

      {error && !loading && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {!loading && !error && news.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📰</div>
          <h3>No news found</h3>
          <p>No news found for {ticker}.</p>
        </div>
      )}

      {!loading && news.length > 0 && (
        <div className="news-grid">
          {news.map((item, i) => (
            <div key={i} className="news-card">
              <div className="news-title">{item.title || '(No title)'}</div>
              <div className="news-meta">
                {item.ticker && (
                  <span className="news-ticker-badge">{item.ticker}</span>
                )}
                {item.source && (
                  <span className="news-source">{item.source}</span>
                )}
                {item.timestamp && (
                  <span>{formatTimestamp(item.timestamp)}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
