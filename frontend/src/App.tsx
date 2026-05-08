import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Bot,
  CheckCircle2,
  Database,
  FileText,
  Loader2,
  LogOut,
  MessageSquareText,
  RefreshCw,
  Send,
  Settings2,
  ShieldCheck,
  Upload,
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

type SourceListResponse = {
  success: boolean
  data: unknown
}

type CacheStats = {
  cached_queries: number
  max_queries: number
  ttl_seconds?: number
  recent_queries: Array<Record<string, unknown>>
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

function compactData(value: unknown) {
  if (!value) return []
  if (Array.isArray(value)) return value
  if (typeof value === 'object') {
    const objectValue = value as Record<string, unknown>
    for (const key of ['sources', 'current_sources', 'documents', 'items']) {
      const maybeList = objectValue[key]
      if (Array.isArray(maybeList)) return maybeList
    }
    return Object.entries(objectValue).map(([key, item]) => ({ key, item }))
  }
  return [value]
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
  const [question, setQuestion] = useState('')
  const [textUpload, setTextUpload] = useState('')
  const [sourceCount, setSourceCount] = useState(3)
  const [useCache, setUseCache] = useState(true)
  const [activeSource, setActiveSource] = useState<string | null>(null)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)
  const [accessToken, setAccessToken] = useState(() =>
    localStorage.getItem(ACCESS_TOKEN_KEY),
  )

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

  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await api.get<{ status: string }>('/api/health')
      return response.data
    },
    retry: false,
  })

  const sourcesQuery = useQuery({
    queryKey: ['sources'],
    queryFn: async () => {
      const response = await api.get<SourceListResponse>('/ingest/sources')
      return response.data
    },
    retry: false,
  })

  const cacheQuery = useQuery({
    queryKey: ['cache-stats'],
    queryFn: async () => {
      const response = await api.get<CacheStats>('/api/cache/stats')
      return response.data
    },
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
        k: sourceCount,
        use_cache: useCache,
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
      setActiveSource(sources[0] ?? null)
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

  const textUploadMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/ingest/upload-text', { text: textUpload })
      return response.data
    },
    onSuccess: (data) => {
      setUploadStatus(data.message ?? 'Text ingested successfully')
      setTextUpload('')
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })

  const fileUploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const response = await api.post('/ingest/upload-file', formData)
      return response.data
    },
    onSuccess: (data) => {
      setUploadStatus(data.message ?? 'File ingested successfully')
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })

  const clearSourcesMutation = useMutation({
    mutationFn: async () => {
      const response = await api.delete('/ingest/clear-all')
      return response.data
    },
    onSuccess: () => {
      setUploadStatus('All sources cleared')
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      setActiveSource(null)
    },
  })

  const sourceItems = useMemo(
    () => compactData(sourcesQuery.data?.data),
    [sourcesQuery.data],
  )

  function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthNotice(null)
    authMutation.mutate()
  }

  function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const prompt = question.trim()
    if (!prompt) return
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: 'user', content: prompt },
    ])
    setQuestion('')
    queryMutation.mutate(prompt)
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
    setActiveSource(null)
    setUploadStatus(null)
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
    <main className="flex h-screen overflow-hidden bg-[#eef2f5] text-[#17202a]">
      <aside className="hidden h-screen w-80 shrink-0 overflow-hidden border-r border-[#d8dee5] bg-white p-4 lg:flex lg:flex-col">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-[8px] bg-[#14213d] text-white">
            <Bot size={21} />
          </div>
          <div>
            <p className="font-semibold">Smart RAG</p>
            <p className="text-xs text-[#6b7a89]">Document chatbot</p>
          </div>
        </div>

        <section className="rounded-[8px] border border-[#d8dee5] p-3">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Sources</h2>
            <button
              title="Refresh sources"
              type="button"
              onClick={() => sourcesQuery.refetch()}
              className="rounded-[6px] p-1.5 text-[#607080] hover:bg-[#edf2f7]"
            >
              <RefreshCw size={15} />
            </button>
          </div>
          <div className="max-h-32 space-y-2 overflow-auto">
            {sourceItems.length === 0 ? (
              <p className="text-sm text-[#6b7a89]">No sources indexed yet.</p>
            ) : (
              sourceItems.map((source, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => setActiveSource(JSON.stringify(source, null, 2))}
                  className="w-full rounded-[6px] border border-[#e4eaf0] px-3 py-2 text-left text-xs text-[#435262] hover:border-[#2ec4b6]"
                >
                  <span className="line-clamp-2">
                    {typeof source === 'string'
                      ? source
                      : JSON.stringify(source).slice(0, 110)}
                  </span>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="mt-4 min-h-0 rounded-[8px] border border-[#d8dee5] p-3">
          <h2 className="mb-3 text-sm font-semibold">Add Knowledge</h2>
          <label className="mb-3 flex cursor-pointer items-center justify-center gap-2 rounded-[8px] border border-dashed border-[#aab7c4] px-3 py-3 text-sm text-[#435262] hover:border-[#2ec4b6]">
            <Upload size={17} />
            Upload file
            <input
              type="file"
              className="hidden"
              accept=".txt,.pdf,.docx"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) fileUploadMutation.mutate(file)
                event.currentTarget.value = ''
              }}
            />
          </label>
          <textarea
            value={textUpload}
            onChange={(event) => setTextUpload(event.target.value)}
            rows={4}
            placeholder="Paste raw text to ingest..."
            className="w-full resize-none rounded-[8px] border border-[#cfd8e3] px-3 py-2 text-sm outline-none focus:border-[#2ec4b6]"
          />
          <button
            type="button"
            onClick={() => textUploadMutation.mutate()}
            disabled={!textUpload.trim() || textUploadMutation.isPending}
            className="mt-2 w-full rounded-[8px] bg-[#2ec4b6] px-3 py-2 text-sm font-semibold text-[#07151b] disabled:opacity-60"
          >
            Ingest text
          </button>
          {uploadStatus && (
            <p className="mt-3 flex items-start gap-2 rounded-[8px] bg-[#ecfdf5] px-3 py-2 text-xs text-[#047857]">
              <CheckCircle2 size={15} /> {uploadStatus}
            </p>
          )}
        </section>

        <button
          type="button"
          onClick={() => clearSourcesMutation.mutate()}
          className="mt-3 rounded-[8px] border border-[#d8dee5] px-3 py-2 text-sm text-[#607080] hover:border-[#ef476f] hover:text-[#be123c]"
        >
          Clear all sources
        </button>
      </aside>

      <section className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden">
        <header className="shrink-0 flex flex-wrap items-center justify-between gap-3 border-b border-[#d8dee5] bg-white px-4 py-3">
          <div>
            <p className="text-sm font-semibold">Chat</p>
            <p className="text-xs text-[#6b7a89]">
              {meQuery.data?.username ?? 'Signed in'} · API{' '}
              {healthQuery.data?.status === 'ok' ? 'online' : 'checking'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 rounded-[8px] border border-[#d8dee5] px-3 py-2 text-sm">
              <Settings2 size={15} />
              k
              <input
                type="number"
                min={1}
                max={10}
                value={sourceCount}
                onChange={(event) => setSourceCount(Number(event.target.value))}
                className="w-10 bg-transparent outline-none"
              />
            </label>
            <label className="flex items-center gap-2 rounded-[8px] border border-[#d8dee5] px-3 py-2 text-sm">
              Cache
              <input
                type="checkbox"
                checked={useCache}
                onChange={(event) => setUseCache(event.target.checked)}
              />
            </label>
            <button
              title="Log out"
              type="button"
              onClick={handleLogout}
              className="rounded-[8px] border border-[#d8dee5] p-2 text-[#607080] hover:bg-white"
            >
              <LogOut size={17} />
            </button>
          </div>
        </header>

        <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-[minmax(0,1fr)_360px]">
          <section className="flex min-h-0 flex-col overflow-hidden">
            <div className="min-h-0 flex-1 space-y-3 overflow-auto p-4">
              {messages.map((message) => (
                <article
                  key={message.id}
                  className={twMerge(
                    'max-w-3xl rounded-[8px] border px-4 py-3 text-sm leading-6 shadow-sm',
                    message.role === 'user'
                      ? 'ml-auto border-[#b8d8d8] bg-[#e8fbf8]'
                      : 'border-[#d8dee5] bg-white',
                  )}
                >
                  <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[#607080]">
                    {message.role === 'assistant' ? (
                      <Bot size={14} />
                    ) : (
                      <MessageSquareText size={14} />
                    )}
                    {message.role}
                    {message.cached && (
                      <span className="rounded-full bg-[#fff3cd] px-2 py-0.5 text-[#8a6100]">
                        cached
                      </span>
                    )}
                  </div>
                  <p className="whitespace-pre-wrap">{message.content}</p>
                  {message.sources?.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {message.sources.map((source, index) => (
                        <button
                          key={index}
                          type="button"
                          onClick={() => setActiveSource(source)}
                          className="rounded-full border border-[#cfd8e3] px-3 py-1 text-xs text-[#435262] hover:border-[#2ec4b6]"
                        >
                          Source {index + 1}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </article>
              ))}
              {queryMutation.isPending && (
                <div className="flex max-w-3xl items-center gap-2 rounded-[8px] border border-[#d8dee5] bg-white px-4 py-3 text-sm text-[#607080]">
                  <Loader2 className="animate-spin" size={17} />
                  Retrieving context and drafting an answer...
                </div>
              )}
            </div>

            <form onSubmit={handleAsk} className="shrink-0 border-t border-[#d8dee5] bg-white p-3">
              <div className="flex gap-3">
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  rows={1}
                  placeholder="Ask a question about your indexed documents..."
                  className="h-12 flex-1 resize-none rounded-[8px] border border-[#cfd8e3] px-3 py-3 text-sm outline-none focus:border-[#2ec4b6]"
                />
                <button
                  type="submit"
                  disabled={!question.trim() || queryMutation.isPending}
                  className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[8px] bg-[#14213d] text-white disabled:opacity-60"
                  title="Send question"
                >
                  <Send size={18} />
                </button>
              </div>
            </form>
          </section>

          <aside className="hidden min-h-0 overflow-hidden border-l border-[#d8dee5] bg-white p-4 lg:flex lg:flex-col">
            <div className="mb-4 shrink-0 rounded-[8px] border border-[#d8dee5] p-3">
              <h2 className="mb-2 text-sm font-semibold">System</h2>
              <div className="grid gap-2 text-xs text-[#607080]">
                <span>API status: {healthQuery.data?.status ?? 'unknown'}</span>
                <span>
                  Cache: {cacheQuery.data?.cached_queries ?? 0}/
                  {cacheQuery.data?.max_queries ?? 0} queries
                </span>
                <span>Sources indexed: {sourceItems.length}</span>
              </div>
            </div>

            <div className="flex min-h-0 flex-1 flex-col rounded-[8px] border border-[#d8dee5]">
              <div className="border-b border-[#d8dee5] px-3 py-2">
                <h2 className="text-sm font-semibold">Retrieved Context</h2>
              </div>
              <pre className="min-h-0 flex-1 whitespace-pre-wrap overflow-auto p-3 text-xs leading-5 text-[#435262]">
                {activeSource ?? 'Select a source from an answer to inspect it here.'}
              </pre>
            </div>
          </aside>
        </div>
      </section>
    </main>
  )
}

export default App
