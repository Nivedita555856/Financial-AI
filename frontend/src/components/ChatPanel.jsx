import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'
import { askQuestion, analyzeImpact } from '../api/client'

const COMPANY_NAMES = {
  AAPL: 'Apple', MSFT: 'Microsoft', GOOGL: 'Alphabet',
  AMZN: 'Amazon', TSLA: 'Tesla', NVDA: 'NVIDIA',
}

const NAME_TO_TICKER = {
  apple: 'AAPL', microsoft: 'MSFT', google: 'GOOGL',
  alphabet: 'GOOGL', amazon: 'AMZN', tesla: 'TSLA', nvidia: 'NVDA',
}

function extractTicker(text) {
  const lower = text.toLowerCase()
  for (const [name, ticker] of Object.entries(NAME_TO_TICKER)) {
    if (lower.includes(name)) return ticker
  }
  return null
}

function formatTime(d) {
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function parseImpactCommand(text) {
  const lower = text.toLowerCase().trim()
  if (!lower.startsWith('impact')) return null
  const rest = text.slice(6)
  const parts = rest.split('|')
  if (parts.length >= 2) {
    return { ticker: parts[0].trim().toUpperCase(), issue: parts[1].trim() }
  }
  return null
}

export default function ChatPanel({ ticker, backendStatus }) {
  const [messages, setMessages] = useState([])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const bottomRef               = useRef(null)
  const textareaRef             = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const QUICK_SUGGESTIONS = [
    `What is ${ticker}'s revenue trend?`,
    `Who competes with ${ticker}?`,
    `Who supplies to ${ticker}?`,
    `Any recent news about ${ticker}?`,
    `impact ${ticker} | supply chain disruption`,
  ]

  async function send(text) {
    const question = (text || input).trim()
    if (!question || loading) return
    setInput('')

    const userMsg = { role: 'user', content: question, time: new Date() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      // Check for impact command
      const impactCmd = parseImpactCommand(question)
      if (impactCmd) {
        const data = await analyzeImpact(impactCmd.ticker, impactCmd.issue)
        const answer = data.analysis || data.error || 'No analysis returned.'
        setMessages(prev => [...prev, { role: 'assistant', content: answer, time: new Date() }])
      } else {
        const detectedTicker = extractTicker(question) || ticker
        const data = await askQuestion(question, detectedTicker)
        const answer = data.answer || data.error || 'No answer returned.'
        setMessages(prev => [...prev, { role: 'assistant', content: answer, time: new Date() }])
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ Error: ${err.message}. Check that the backend is running.`,
        time: new Date(),
      }])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="chat-container">
      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 && !loading && (
          <div className="chat-welcome">
            <div className="chat-welcome-icon">📈</div>
            <h2>{COMPANY_NAMES[ticker] || ticker}</h2>
            {backendStatus === 'offline' && (
              <div className="offline-warn" style={{ textAlign: 'left', margin: '0 auto 16px', maxWidth: 360 }}>
                <div className="offline-warn-icon">⚠️</div>
                <div>
                  <div className="offline-warn-title">Backend offline</div>
                  <div className="offline-warn-body">Render free tier may be sleeping — first request takes ~30s.</div>
                </div>
              </div>
            )}
            <div className="quick-chips">
              {QUICK_SUGGESTIONS.map(q => (
                <button key={q} className="chip" onClick={() => send(q)}>{q}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="msg-avatar">
              {msg.role === 'user' ? '👤' : '🤖'}
            </div>
            <div>
              <div className="msg-bubble">{msg.content}</div>
              <div className="msg-time">{formatTime(msg.time)}</div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="msg-avatar">🤖</div>
            <div className="typing-indicator">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <div className="chat-input-row">
          <textarea
            ref={textareaRef}
            className="chat-input"
            rows={1}
            placeholder={`Ask about ${ticker}… or type "impact ${ticker} | issue"`}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={e => {
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
            }}
            disabled={loading}
          />
          <button className="send-btn" onClick={() => send()} disabled={!input.trim() || loading}>
            <Send size={18} />
          </button>
        </div>
        <div className="chat-hint">Enter to send · Shift+Enter new line</div>
      </div>
    </div>
  )
}
