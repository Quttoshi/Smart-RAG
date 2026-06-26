import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Bot,
  Database,
  FileText,
  Loader2,
  X,
  LogOut,
  PanelLeft,
  Plus,
  Send,
  ShieldCheck,
} from 'lucide-react'
import axios from 'axios'
import { twMerge } from 'tailwind-merge'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const ACCESS_TOKEN_KEY = 'smart-rag-access-token'
const REFRESH_TOKEN_KEY = 'smart-rag-refresh-token'

type AuthMode = 'login' | 'register'

type User = {
  id: string
  username: string
  email: string
  is_active: boolean
  is_admin: boolean
  created_at: string
}

type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
}

type QueryResponse = {
  answer: string
  context: string
  num_sources: number
  sources?: string[]
  cached: boolean
}

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: string[]
  cached?: boolean
}

const emptyAuthForm = {
  username: '',
  email: '',
  password: '',
}

const api = axios.create({
  baseURL: API_BASE_URL,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    return error.message
  }
  if (error instanceof Error) return error.message
  return 'Something went wrong'
}

function App() {
  const queryClient = useQueryClient()
  const [authMode, setAuthMode] = useState<AuthMode>('login')
  const [authForm, setAuthForm] = useState(emptyAuthForm)
  const [authNotice, setAuthNotice] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Upload a document or paste text, then ask me questions grounded in your sources.',
    },
  ])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [question, setQuestion] = useState('')
  const [hasStarted, setHasStarted] = useState(false)
  const [attachedFile, setAttachedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [accessToken, setAccessToken] = useState(() =>
    localStorage.getItem(ACCESS_TOKEN_KEY),
  )

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const isAuthed = Boolean(accessToken)

  const meQuery = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      const response = await api.get<User>('/api/auth/me')
      return response.data
    },
    enabled: isAuthed,
    retry: false,
  })


  const authMutation = useMutation({
    mutationFn: async () => {
      if (authMode === 'register') {
        const response = await api.post('/api/auth/register', authForm)
        return { mode: 'register' as const, data: response.data }
      }
      const response = await api.post<TokenResponse>('/api/auth/login', {
        username: authForm.username,
        password: authForm.password,
      })
      return { mode: 'login' as const, data: response.data }
    },
    onSuccess: (result) => {
      if (result.mode === 'register') {
        setAuthNotice('Registration successful. You can log in now.')
        setAuthMode('login')
        setAuthForm((current) => ({
          username: current.username,
          email: '',
          password: '',
        }))
        return
      }

      localStorage.setItem(ACCESS_TOKEN_KEY, result.data.access_token)
      localStorage.setItem(REFRESH_TOKEN_KEY, result.data.refresh_token)
      setAccessToken(result.data.access_token)
      setAuthNotice(null)
      setAuthForm(emptyAuthForm)
      queryClient.invalidateQueries()
    },
  })

  const queryMutation = useMutation({
    mutationFn: async (prompt: string) => {
      const response = await api.post<QueryResponse>('/api/query', {
        question: prompt,
        k: 3,
        use_cache: true,
      })
      return response.data
    },
    onSuccess: (data) => {
      const sources = data.sources?.length
        ? data.sources
        : data.context
          ? [data.context]
          : []
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.answer,
          sources,
          cached: data.cached,
        },
      ])
      queryClient.invalidateQueries({ queryKey: ['cache-stats'] })
    },
    onError: (error) => {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: getErrorMessage(error),
        },
      ])
    },
  })

  const fileUploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const response = await api.post('/ingest/upload-file', formData)
      return response.data
    },
  })

  function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthNotice(null)
    authMutation.mutate()
  }

  function submitQuestion() {
    const prompt = question.trim()
    if (!prompt || queryMutation.isPending) return
    setHasStarted(true)
    setAttachedFile(null)
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: 'user', content: prompt },
    ])
    setQuestion('')
    if (textareaRef.current) textareaRef.current.style.height = '52px'
    queryMutation.mutate(prompt)
  }

  function handleNewChat() {
    setHasStarted(false)
    setAttachedFile(null)
    setMessages([{ id: 'welcome', role: 'assistant', content: 'Upload a document or paste text, then ask me questions grounded in your sources.' }])
    setQuestion('')
    if (textareaRef.current) textareaRef.current.style.height = '52px'
  }

  function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    submitQuestion()
  }

  function handleLogout() {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    setAccessToken(null)
    setAuthMode('login')
    setAuthForm(emptyAuthForm)
    setAuthNotice(null)
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content:
          'Upload a document or paste text, then ask me questions grounded in your sources.',
      },
    ])
    setHasStarted(false)
    queryClient.clear()
  }

  if (!isAuthed) {
    return (
      <main className="min-h-screen bg-[#eef2f5] px-4 py-8 text-[#17202a]">
        <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl overflow-hidden rounded-[8px] border border-[#d8dee5] bg-white shadow-sm md:grid-cols-[1.1fr_0.9fr]">
          <div className="flex flex-col justify-between bg-[#14213d] p-8 text-white">
            <div>
              <div className="mb-10 flex h-11 w-11 items-center justify-center rounded-[8px] bg-[#2ec4b6] text-[#07151b]">
                <Bot size={24} />
              </div>
              <h1 className="max-w-lg text-4xl font-semibold leading-tight">
                Smart RAG, shaped as a document chatbot.
              </h1>
              <p className="mt-4 max-w-xl text-sm leading-6 text-[#cbd5e1]">
                Ask questions, inspect retrieved context, and keep document ingestion
                close to the conversation.
              </p>
            </div>
            <div className="mt-10 grid gap-3 text-sm text-[#dbeafe]">
              <span className="flex items-center gap-2">
                <ShieldCheck size={17} /> JWT-protected workspace
              </span>
              <span className="flex items-center gap-2">
                <FileText size={17} /> PDF, DOCX, and TXT ingestion
              </span>
              <span className="flex items-center gap-2">
                <Database size={17} /> FAISS retrieval with Redis cache
              </span>
            </div>
          </div>

          <form onSubmit={handleAuthSubmit} className="flex flex-col justify-center p-6 sm:p-10">
            <div className="mb-6">
              <p className="text-sm font-medium text-[#607080]">Welcome</p>
              <h2 className="mt-2 text-2xl font-semibold">
                {authMode === 'login' ? 'Log in to chat' : 'Create your account'}
              </h2>
            </div>

            <div className="mb-6 grid grid-cols-2 rounded-[8px] bg-[#edf2f7] p-1 text-sm">
              {(['login', 'register'] as AuthMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => {
                    setAuthMode(mode)
                    setAuthNotice(null)
                  }}
                  className={twMerge(
                    'rounded-[6px] px-3 py-2 font-medium capitalize text-[#607080]',
                    authMode === mode && 'bg-white text-[#17202a] shadow-sm',
                  )}
                >
                  {mode}
                </button>
              ))}
            </div>

            <label className="mb-4 grid gap-2 text-sm font-medium">
              Username
              <input
                value={authForm.username}
                onChange={(event) =>
                  setAuthForm((current) => ({ ...current, username: event.target.value }))
                }
                className="rounded-[8px] border border-[#cfd8e3] px-3 py-2 outline-none focus:border-[#2ec4b6]"
                required
              />
            </label>

            {authMode === 'register' && (
              <label className="mb-4 grid gap-2 text-sm font-medium">
                Email
                <input
                  type="email"
                  value={authForm.email}
                  onChange={(event) =>
                    setAuthForm((current) => ({ ...current, email: event.target.value }))
                  }
                  className="rounded-[8px] border border-[#cfd8e3] px-3 py-2 outline-none focus:border-[#2ec4b6]"
                  required
                />
              </label>
            )}

            <label className="mb-5 grid gap-2 text-sm font-medium">
              Password
              <input
                type="password"
                value={authForm.password}
                onChange={(event) =>
                  setAuthForm((current) => ({ ...current, password: event.target.value }))
                }
                className="rounded-[8px] border border-[#cfd8e3] px-3 py-2 outline-none focus:border-[#2ec4b6]"
                required
              />
            </label>

            {authMutation.isError && (
              <p className="mb-4 rounded-[8px] bg-[#fff1f2] px-3 py-2 text-sm text-[#be123c]">
                {getErrorMessage(authMutation.error)}
              </p>
            )}

            {authNotice && (
              <p className="mb-4 rounded-[8px] bg-[#ecfdf5] px-3 py-2 text-sm text-[#047857]">
                {authNotice}
              </p>
            )}

            <button
              type="submit"
              disabled={authMutation.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-[8px] bg-[#14213d] px-4 py-3 text-sm font-semibold text-white disabled:opacity-70"
            >
              {authMutation.isPending && <Loader2 className="animate-spin" size={17} />}
              {authMode === 'login' ? 'Log in' : 'Register'}
            </button>
          </form>
        </section>
      </main>
    )
  }

  return (
    <main className="flex h-screen overflow-hidden bg-[#171717] text-white">
      {/* Sidebar */}
      <aside className={twMerge('h-screen shrink-0 overflow-hidden border-r border-white/10 bg-[#212121] flex flex-col transition-[width] duration-300', sidebarOpen ? 'w-64' : 'w-14')}>
        {/* Toggle row */}
        <div className="flex items-center gap-3 px-3 pt-3 pb-1">
          <button
            title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            type="button"
            onClick={() => setSidebarOpen((o) => !o)}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] text-white/40 hover:text-white hover:bg-white/10"
          >
            <PanelLeft size={17} />
          </button>
          <div className={twMerge('flex items-center gap-2 whitespace-nowrap transition-opacity duration-200', sidebarOpen ? 'opacity-100 delay-150' : 'opacity-0 pointer-events-none')}>
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[6px] bg-[#2ec4b6] text-[#07151b]">
              <Bot size={13} />
            </div>
            <p className="font-semibold text-white text-sm">Smart RAG</p>
          </div>
        </div>

        {/* New chat row */}
        <div className="flex items-center gap-3 px-3 mt-4 mb-2">
          <button
            type="button"
            onClick={handleNewChat}
            title="New chat"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] bg-white/10 hover:bg-white/15 text-white/70 hover:text-white transition-colors"
          >
            <Plus size={16} />
          </button>
          <span className={twMerge('text-sm text-white/60 whitespace-nowrap transition-opacity duration-200', sidebarOpen ? 'opacity-100 delay-150' : 'opacity-0 pointer-events-none')}>New chat</span>
        </div>

        {/* Recents */}
        <div className={twMerge('flex flex-1 flex-col overflow-hidden px-3 whitespace-nowrap transition-opacity duration-200', sidebarOpen ? 'opacity-100 delay-150' : 'opacity-0 pointer-events-none')}>
          <p className="mt-4 mb-2 text-xs font-semibold uppercase tracking-wide text-white/30">Recents</p>
          <div className="flex-1 space-y-1 overflow-auto">
            {messages.filter((m) => m.role === 'user').length === 0 ? (
              <p className="text-xs text-white/25 whitespace-normal">No questions yet.</p>
            ) : (
              messages.filter((m) => m.role === 'user').map((m) => (
                <div key={m.id} className="rounded-[8px] px-2 py-2 text-xs text-white/60 bg-white/5 line-clamp-2 hover:bg-white/10 cursor-default whitespace-normal">
                  {m.content}
                </div>
              ))
            )}
          </div>
        </div>
      </aside>

      {/* Main */}
      <section className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden">
        <header className="shrink-0 flex items-center justify-end px-4 py-3 border-b border-white/10">
          <button
            title="Log out"
            type="button"
            onClick={handleLogout}
            className="rounded-[8px] p-2 text-white/40 hover:text-white hover:bg-white/10"
          >
            <LogOut size={17} />
          </button>
        </header>

        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.pdf,.docx"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) { setAttachedFile(file); fileUploadMutation.mutate(file) }
            event.currentTarget.value = ''
          }}
        />

        {hasStarted ? (
          <>
            <div className="min-h-0 flex-1 overflow-auto px-4 py-6 space-y-4">
              {messages.map((message) => (
                <article
                  key={message.id}
                  className={twMerge(
                    'max-w-2xl mx-auto rounded-2xl px-4 py-3 text-base leading-7',
                    message.role === 'user'
                      ? 'ml-auto bg-[#2f2f2f] text-[#e5e7eb]'
                      : 'text-[#e5e7eb]',
                  )}
                >
                  {message.role === 'assistant' && (
                    <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-white/40">
                      <Bot size={13} /> Assistant
                    </div>
                  )}
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </article>
              ))}
              {queryMutation.isPending && (
                <div className="max-w-2xl mx-auto flex items-center gap-2 text-sm text-white/30">
                  <Loader2 className="animate-spin" size={15} /> Thinking…
                </div>
              )}
              {fileUploadMutation.isPending && (
                <div className="max-w-2xl mx-auto flex items-center gap-2 text-sm text-white/30">
                  <Loader2 className="animate-spin" size={15} /> Uploading file…
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="shrink-0 px-4 pb-4 pt-2">
              <form onSubmit={handleAsk} className="mx-auto max-w-2xl">
                {attachedFile && (
                  <div className="mb-2 flex items-center gap-2 rounded-lg bg-white/10 px-3 py-1.5 w-fit ml-2">
                    <FileText size={13} className="text-white/50 shrink-0" />
                    <span className="text-xs text-white/70 truncate max-w-[200px]">{attachedFile.name}</span>
                    <button type="button" onClick={() => setAttachedFile(null)} className="text-white/40 hover:text-white ml-1"><X size={12} /></button>
                  </div>
                )}
                <div className="flex items-center gap-2 rounded-full bg-[#2f2f2f] border border-[#555555] px-3 py-2">
                  <button type="button" title="Upload file" onClick={() => fileInputRef.current?.click()} disabled={fileUploadMutation.isPending} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white/40 hover:text-white hover:bg-white/10 disabled:opacity-30">
                    <Plus size={20} />
                  </button>
                  <textarea
                    ref={textareaRef}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onInput={(e) => { const el = e.currentTarget; el.style.height = '28px'; el.style.height = `${el.scrollHeight}px` }}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitQuestion() } }}
                    rows={1}
                    placeholder="Ask a follow-up…"
                    className="flex-1 bg-transparent text-white/90 placeholder-white/30 resize-none overflow-hidden outline-none text-sm leading-7"
                    style={{ minHeight: '28px', maxHeight: '160px' }}
                  />
                  <button type="submit" disabled={!question.trim() || queryMutation.isPending} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-[#212121] disabled:opacity-20" title="Send">
                    <Send size={14} />
                  </button>
                </div>
              </form>
            </div>
          </>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center px-4 pb-32">
            <h1 className="mb-6 text-2xl font-semibold text-white/80">
              {meQuery.data?.username && <span>{meQuery.data.username}, </span>}How can I help you today?
            </h1>
            <form onSubmit={handleAsk} className="w-full max-w-2xl">
              {attachedFile && (
                <div className="mb-2 flex items-center gap-2 rounded-lg bg-white/10 px-3 py-1.5 w-fit ml-2">
                  <FileText size={13} className="text-white/50 shrink-0" />
                  <span className="text-xs text-white/70 truncate max-w-[200px]">{attachedFile.name}</span>
                  <button type="button" onClick={() => setAttachedFile(null)} className="text-white/40 hover:text-white ml-1"><X size={12} /></button>
                </div>
              )}
              <div className="flex items-center gap-2 rounded-full bg-[#2f2f2f] border border-[#555555] px-3 py-2">
                <button type="button" title="Upload file" onClick={() => fileInputRef.current?.click()} disabled={fileUploadMutation.isPending} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white/40 hover:text-white hover:bg-white/10 disabled:opacity-30">
                  {fileUploadMutation.isPending ? <Loader2 className="animate-spin" size={14} /> : <Plus size={20} />}
                </button>
                <textarea
                  ref={textareaRef}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onInput={(e) => { const el = e.currentTarget; el.style.height = '28px'; el.style.height = `${el.scrollHeight}px` }}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitQuestion() } }}
                  rows={1}
                  placeholder="Ask anything about your documents…"
                  className="flex-1 bg-transparent text-white/90 placeholder-white/30 resize-none overflow-hidden outline-none text-sm leading-7"
                  style={{ minHeight: '28px', maxHeight: '160px' }}
                />
                <button type="submit" disabled={!question.trim() || queryMutation.isPending} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-[#212121] disabled:opacity-20" title="Send">
                  <Send size={14} />
                </button>
              </div>
            </form>
          </div>
        )}
      </section>
    </main>
  )
}

export default App
