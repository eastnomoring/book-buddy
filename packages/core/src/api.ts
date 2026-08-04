import type {
  ChatRequest,
  ChatResponse,
  BookInfo,
  BookUploadResult,
  AppConfig,
  ConfigUpdatePayload,
  ConfigTestResult,
} from './types.js'

export const API_PATHS = {
  CHAT: '/chat',
  CHAT_STREAM: '/chat/stream',
  BOOKS: '/books',
  BOOKS_UPLOAD: '/books/upload',
  VOICE_TRANSCRIBE: '/voice/transcribe',
  VOICE_SYNTHESIZE: '/voice/synthesize',
  CONFIG: '/config',
  CONFIG_TEST: '/config/test',
} as const

export function buildChatBody(request: ChatRequest): Record<string, unknown> {
  return {
    text: request.text,
    image: request.image,
    media_type: request.mediaType,
    audio: request.audio,
    book_id: request.bookId,
    page_number: request.pageNumber,
    history: request.history,
    enable_tts: request.enableTts,
  }
}

export function mapChatResponse(raw: Record<string, unknown>): ChatResponse {
  return {
    text: String(raw.text ?? ''),
    audio: raw.audio ? String(raw.audio) : undefined,
    sources: (raw.sources as string[]) || [],
    pageReferences: (raw.page_references as number[])
      || (raw.pageReferences as number[])
      || [],
  }
}

export function mapBookInfo(raw: Record<string, unknown>): BookInfo {
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

export function mapUploadResult(raw: Record<string, unknown>): BookUploadResult {
  return {
    id: String(raw.id ?? ''),
    title: String(raw.title ?? ''),
    message: String(raw.message ?? ''),
  }
}

export function mapConfig(raw: Record<string, unknown>): AppConfig {
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

export function buildConfigUpdateBody(
  payload: ConfigUpdatePayload,
): Record<string, unknown> {
  return {
    provider: payload.provider,
    api_key: payload.apiKey || undefined,
    base_url: payload.baseUrl || undefined,
    model: payload.model || undefined,
    voice_api_key: payload.voiceApiKey || undefined,
  }
}

export function buildConfigTestBody(
  payload: ConfigUpdatePayload,
): Record<string, unknown> {
  return {
    provider: payload.provider,
    api_key: payload.apiKey || undefined,
    base_url: payload.baseUrl || undefined,
    model: payload.model || undefined,
  }
}

export function mapTestResult(raw: Record<string, unknown>): ConfigTestResult {
  return { ok: Boolean(raw.ok), message: String(raw.message ?? '') }
}
