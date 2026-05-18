/**
 * API client for Financial Insights Copilot
 * Uses VITE_API_URL env var in production; falls back to relative URLs (Vite proxy) in dev
 */

const API_URL = import.meta.env.VITE_API_URL || ''

const DEFAULT_TIMEOUT = 90_000 // 90s — Groq LLM can be slow

async function fetchWithTimeout(url, options = {}, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)
  try {
    const response = await fetch(url, { ...options, signal: controller.signal })
    return response
  } finally {
    clearTimeout(id)
  }
}

export async function checkHealth() {
  try {
    const res = await fetchWithTimeout(`${API_URL}/health`, {}, 8_000)
    if (!res.ok) return { status: 'offline' }
    return res.json()
  } catch {
    return { status: 'offline' }
  }
}

export async function getCompanies() {
  const res = await fetchWithTimeout(`${API_URL}/api/companies`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function askQuestion(question, ticker) {
  const body = { question }
  if (ticker) body.ticker = ticker
  const res = await fetchWithTimeout(`${API_URL}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function analyzeImpact(ticker, issue) {
  const res = await fetchWithTimeout(`${API_URL}/api/impact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker, issue }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getFinancials(ticker) {
  const res = await fetchWithTimeout(`${API_URL}/api/financials/${ticker}`, {}, 30_000)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getNews(ticker, limit = 6) {
  const res = await fetchWithTimeout(`${API_URL}/api/news/${ticker}?limit=${limit}`, {}, 20_000)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
