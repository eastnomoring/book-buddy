export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface ChatRequest {
  text?: string
  image?: string
  /** 图片媒体类型，如 image/jpeg、image/png、image/webp；
   *  后端据此拼 data URI，缺省回退 image/jpeg */
  mediaType?: string
  audio?: string
  bookId?: string
  pageNumber?: number
  history?: ChatMessage[]
  /** Z4：服务端按句 TTS，经 type=audio 事件下发 */
  enableTts?: boolean
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
