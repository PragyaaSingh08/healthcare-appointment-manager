import { useEffect, useRef, useState } from 'react'
import { chatApi, apiErrorMessage } from '../../services/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const SUGGESTED_PROMPTS = [
  'Find a dermatologist',
  'Show my upcoming appointments',
  'Help me reschedule',
  'What did my last visit say?',
  'Show my medication schedule',
]

export default function ChatAssistant() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatApi.createSession().then(({ data }) => setSessionId(data.id))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  async function send(text: string) {
    if (!sessionId || !text.trim()) return
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')
    setSending(true)
    try {
      const { data } = await chatApi.sendMessage(sessionId, text)
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="p-8 max-w-2xl h-screen flex flex-col">
      <h1 className="font-display text-3xl text-forest-900 mb-1">Assistant</h1>
      <p className="text-ink-400 mb-6">
        Ask about doctors, appointments, or your care plan. This assistant can't diagnose or prescribe.
      </p>

      <div className="card flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {messages.length === 0 && (
            <div className="flex flex-wrap gap-2 pt-4">
              {SUGGESTED_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => send(p)}
                  className="text-sm rounded-full border border-forest-100 px-3 py-1.5 hover:border-forest-600 hover:bg-forest-50 transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[80%] rounded-card px-4 py-2.5 text-sm ${
                  m.role === 'user' ? 'bg-forest-700 text-white' : 'bg-sage-100 text-ink-900'
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-sage-100 rounded-card px-4 py-2.5 text-sm text-ink-400">Typing…</div>
            </div>
          )}
          {error && <p className="text-clay-500 text-sm">{error}</p>}
          <div ref={bottomRef} />
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            send(input)
          }}
          className="border-t border-forest-100 p-3 flex gap-2"
        >
          <input
            className="input"
            placeholder="Type a message…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={!sessionId || sending}
          />
          <button type="submit" className="btn-primary" disabled={!sessionId || sending || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
