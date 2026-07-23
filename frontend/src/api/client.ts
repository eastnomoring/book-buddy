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

export interface VoiceTranscribeResponse {
  text: string
  duration: number
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
  return response.data
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
    
    // 解析 SSE 格式
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          if (data.delta) {
            yield data.delta
          }
          if (data.done) {
            return
          }
        } catch {
          // 忽略解析错误
        }
      }
    }
  }
}

// 书籍
export async function listBooks(): Promise<BookInfo[]> {
  const response = await api.get('/books')
  return response.data
}

export async function uploadBook(file: File, title?: string): Promise<BookInfo> {
  const formData = new FormData()
  formData.append('file', file)
  if (title) {
    formData.append('title', title)
  }
  
  const response = await api.post('/books/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

// 语音
export async function transcribeVoice(audioBase64: string, format: string = 'webm'): Promise<VoiceTranscribeResponse> {
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