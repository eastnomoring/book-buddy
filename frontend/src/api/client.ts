// API 客户端
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface ChatRequest {
  text?: string
  image?: string
  audio?: string
  bookId?: string
  pageNumber?: number
  history?: ChatMessage[]
}

export interface ChatResponse {
  text: string
  audio?: string
  sources: string[]
  pageReferences: number[]
}

export interface BookInfo {
  id: string
  title: string
  author?: string
  totalPages: number
  chapters: Array<{ title: string; startPage: number }>
}

export interface BookUploadResult {
  id: string
  title: string
  message: string
}

export interface VoiceTranscribeResponse {
  text: string
  duration: number
}

export interface AppConfig {
  provider: string
  baseUrl?: string
  model: string
  apiKeyMasked: string
  configured: boolean
  voiceConfigured: boolean
  voiceApiKeyMasked: string
}

export interface ConfigUpdatePayload {
  provider: string
  apiKey?: string
  baseUrl?: string
  model?: string
  voiceApiKey?: string
}

export interface ConfigTestResult {
  ok: boolean
  message: string
}

function mapBookInfo(raw: Record<string, unknown>): BookInfo {
  const chaptersRaw = (raw.chapters as Array<Record<string, unknown>>) || []
  return {
    id: String(raw.id ?? ''),
    title: String(raw.title ?? ''),
    author: raw.author ? String(raw.author) : undefined,
    totalPages: Number(raw.total_pages ?? raw.totalPages ?? 0),
    chapters: chaptersRaw.map((c) => ({
      title: String(c.title ?? ''),
      startPage: Number(c.start_page ?? c.startPage ?? 0),
    })),
  }
}

function mapChatResponse(raw: Record<string, unknown>): ChatResponse {
  return {
    text: String(raw.text ?? ''),
    audio: raw.audio ? String(raw.audio) : undefined,
    sources: (raw.sources as string[]) || [],
    pageReferences: (raw.page_references as number[])
      || (raw.pageReferences as number[])
      || [],
  }
}

// 对话
export async function sendChat(request: ChatRequest): Promise<ChatResponse> {
  const response = await api.post('/chat', {
    text: request.text,
    image: request.image,
    audio: request.audio,
    book_id: request.bookId,
    page_number: request.pageNumber,
    history: request.history,
  })
  return mapChatResponse(response.data)
}

// 流式对话
export async function* streamChat(request: ChatRequest): AsyncGenerator<string> {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text: request.text,
      image: request.image,
      book_id: request.bookId,
      page_number: request.pageNumber,
      history: request.history,
    }),
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) return

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue

      let data: { delta?: string; done?: boolean; error?: string }
      try {
        data = JSON.parse(line.slice(6))
      } catch {
        continue
      }

      if (data.error) {
        throw new Error(String(data.error))
      }
      if (data.delta) {
        yield data.delta
      }
      if (data.done) {
        return
      }
    }
  }
}

// 书籍
export async function listBooks(): Promise<BookInfo[]> {
  const response = await api.get('/books')
  return (response.data as Record<string, unknown>[]).map(mapBookInfo)
}

export async function uploadBook(file: File, title?: string): Promise<BookUploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  if (title) {
    formData.append('title', title)
  }

  const response = await api.post('/books/upload', formData)
  const raw = response.data as Record<string, unknown>
  return {
    id: String(raw.id ?? ''),
    title: String(raw.title ?? ''),
    message: String(raw.message ?? ''),
  }
}

// 语音
export async function transcribeVoice(
  audioBase64: string,
  format: string = 'webm',
): Promise<VoiceTranscribeResponse> {
  const response = await api.post('/voice/transcribe', {
    audio: audioBase64,
    format,
  })
  return response.data
}

export async function synthesizeVoice(text: string, voice?: string): Promise<string> {
  const response = await api.post('/voice/synthesize', {
    text,
    voice,
  })
  return response.data.audio
}

// 配置
function mapConfig(raw: Record<string, unknown>): AppConfig {
  return {
    provider: String(raw.provider ?? 'openai'),
    baseUrl: raw.base_url ? String(raw.base_url) : undefined,
    model: String(raw.model ?? ''),
    apiKeyMasked: String(raw.api_key_masked ?? ''),
    configured: Boolean(raw.configured),
    voiceConfigured: Boolean(raw.voice_configured),
    voiceApiKeyMasked: String(raw.voice_api_key_masked ?? ''),
  }
}

export async function getConfig(): Promise<AppConfig> {
  const response = await api.get('/config')
  return mapConfig(response.data as Record<string, unknown>)
}

export async function updateConfig(payload: ConfigUpdatePayload): Promise<AppConfig> {
  const response = await api.put('/config', {
    provider: payload.provider,
    api_key: payload.apiKey || undefined,
    base_url: payload.baseUrl || undefined,
    model: payload.model || undefined,
    voice_api_key: payload.voiceApiKey || undefined,
  })
  return mapConfig(response.data as Record<string, unknown>)
}

export async function testConfig(payload: ConfigUpdatePayload): Promise<ConfigTestResult> {
  const response = await api.post('/config/test', {
    provider: payload.provider,
    api_key: payload.apiKey || undefined,
    base_url: payload.baseUrl || undefined,
    model: payload.model || undefined,
  })
  const raw = response.data as Record<string, unknown>
  return { ok: Boolean(raw.ok), message: String(raw.message ?? '') }
}
