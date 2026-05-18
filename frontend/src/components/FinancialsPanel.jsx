import { useState, useEffect } from 'react'
import { getFinancials } from '../api/client'
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

const COMPANY_NAMES = {
  AAPL: 'Apple Inc.', MSFT: 'Microsoft Corp.', GOOGL: 'Alphabet Inc.',
  AMZN: 'Amazon.com', TSLA: 'Tesla Inc.', NVDA: 'NVIDIA Corp.',
}

function fmtB(val) {
  if (!val || val === 0) return 'N/A'
  const b = parseFloat(val) / 1e9
  if (isNaN(b)) return 'N/A'
  return `$${b.toFixed(1)}B`
}

function fmtShort(val) {
  if (!val || val === 0) return 'N/A'
  const b = parseFloat(val) / 1e9
  if (isNaN(b)) return 'N/A'
  return b.toFixed(1)
}

const TOOLTIP_STYLE = {
  contentStyle: { background: '#0c1829', border: '1px solid #1a2e4a', borderRadius: 8, color: '#e2eaf6', fontSize: 12 },
  itemStyle: { color: '#e2eaf6' },
  labelStyle: { color: '#8ba3c4' },
}

export default function FinancialsPanel({ ticker, backendStatus }) {
  const [data, setData]     = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState(null)

  useEffect(() => {
    loadData()
  }, [ticker])

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const res = await getFinancials(ticker)
      const rows = (res.financials || []).filter(r => r.year)
      // Convert to chart-friendly objects
      const chartData = rows.map(r => ({
        year: String(r.year),
        Revenue:    r.revenue    ? parseFloat(r.revenue)    / 1e9 : 0,
        NetIncome:  r.net_income ? parseFloat(r.net_income) / 1e9 : 0,
        TotalAssets:r.total_assets ? parseFloat(r.total_assets) / 1e9 : 0,
        raw: r,
      }))
      setData(chartData)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return (
    <div className="panel">
      <div className="loading-center"><div className="spinner" /><span>Loading financial data…</span></div>
    </div>
  )

  if (error) return (
    <div className="panel">
      <div className="error-banner">⚠️ {error}</div>
    </div>
  )

  const latest = data[data.length - 1]

  return (
    <div className="panel">
      <div className="section-header">
        <div>
          <div className="section-title">{COMPANY_NAMES[ticker] || ticker} — Financials</div>
        </div>
        <button className="refresh-btn" onClick={loadData}>↺ Refresh</button>
      </div>

      {backendStatus === 'offline' && (
        <div className="offline-warn">
          <div className="offline-warn-icon">⚠️</div>
          <div>
            <div className="offline-warn-title">Backend offline</div>
            <div className="offline-warn-body">Data may not load until the backend wakes up on Render.</div>
          </div>
        </div>
      )}

      {data.length === 0 && !loading ? (
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <h3>No financial data found</h3>
          <p>No data for {ticker}.</p>
        </div>
      ) : (
        <>
          {/* Metric cards */}
          {latest && (
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-label">Revenue</div>
                <div className="metric-value">{fmtB(latest.raw.revenue)}</div>
                <div className="metric-year">Year {latest.year}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Net Income</div>
                <div className={`metric-value ${latest.NetIncome >= 0 ? 'green' : ''}`}>
                  {fmtB(latest.raw.net_income)}
                </div>
                <div className="metric-year">Year {latest.year}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Total Assets</div>
                <div className="metric-value purple">{fmtB(latest.raw.total_assets)}</div>
                <div className="metric-year">Year {latest.year}</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Data Points</div>
                <div className="metric-value" style={{ fontSize: 22 }}>{data.length}</div>
                <div className="metric-year">annual records</div>
              </div>
            </div>
          )}

          {/* Revenue chart */}
          <div className="chart-card">
            <div className="chart-title">Revenue (Billions USD)</div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#00d4ff" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#00d4ff" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2e4a" />
                <XAxis dataKey="year" tick={{ fill: '#8ba3c4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#8ba3c4', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={v => `$${v}B`} />
                <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`$${v.toFixed(1)}B`, 'Revenue']} />
                <Area type="monotone" dataKey="Revenue" stroke="#00d4ff" strokeWidth={2} fill="url(#revGrad)" dot={{ fill: '#00d4ff', r: 3 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Net Income & Assets chart */}
          <div className="chart-card">
            <div className="chart-title">Net Income vs Total Assets (Billions USD)</div>
            <div className="legend">
              <div className="legend-item"><div className="legend-dot" style={{ background: '#00e87a' }} /><span>Net Income</span></div>
              <div className="legend-item"><div className="legend-dot" style={{ background: '#a78bfa' }} /><span>Total Assets</span></div>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a2e4a" />
                <XAxis dataKey="year" tick={{ fill: '#8ba3c4', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#8ba3c4', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={v => `$${v}B`} />
                <Tooltip {...TOOLTIP_STYLE} formatter={(v, name) => [`$${v.toFixed(1)}B`, name]} />
                <Bar dataKey="NetIncome"   name="Net Income"   fill="#00e87a" radius={[3, 3, 0, 0]} opacity={0.85} />
                <Bar dataKey="TotalAssets" name="Total Assets" fill="#a78bfa" radius={[3, 3, 0, 0]} opacity={0.85} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
