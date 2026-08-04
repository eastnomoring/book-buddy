// API 客户端（Web 传输层）
import axios from 'axios'
import {
  API_PATHS,
  buildChatBody,
  buildConfigUpdateBody,
  buildConfigTestBody,
  mapChatResponse,
  mapBookInfo,
  mapUploadResult,
  mapConfig,
  mapTestResult,
  type ChatRequest,
  type ChatResponse,
  type BookInfo,
  type BookUploadResult,
  type VoiceTranscribeResponse,
  type AppConfig,
  type ConfigUpdatePayload,
  type ConfigTestResult,
} from '@book-buddy/core'

export type {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  BookInfo,
  BookUploadResult,
  VoiceTranscribeResponse,
  AppConfig,
  ConfigUpdatePayload,
  ConfigTestResult,
} from '@book-buddy/core'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// 对话
export async function sendChat(request: ChatRequest): Promise<ChatResponse> {
  const response = await api.post(API_PATHS.CHAT, buildChatBody(request))
  return mapChatResponse(response.data)
}

// 流式对话已迁移至 platform/index.ts 的 chatStream（走 ChatTransport 接口实现），
// 本文件不再提供 streamChat，避免双路径并存。

// 书籍
export async function listBooks(): Promise<BookInfo[]> {
  const response = await api.get(API_PATHS.BOOKS)
  return (response.data as Record<string, unknown>[]).map(mapBookInfo)
}

export async function uploadBook(file: File, title?: string): Promise<BookUploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  if (title) {
    formData.append('title', title)
  }

  const response = await api.post(API_PATHS.BOOKS_UPLOAD, formData)
  return mapUploadResult(response.data)
}

// 语音
export async function transcribeVoice(
  audioBase64: string,
  format: string = 'webm',
): Promise<VoiceTranscribeResponse> {
  const response = await api.post(API_PATHS.VOICE_TRANSCRIBE, {
    audio: audioBase64,
    format,
  })
  return response.data
}

export async function synthesizeVoice(text: string, voice?: string): Promise<string> {
  const response = await api.post(API_PATHS.VOICE_SYNTHESIZE, {
    text,
    voice,
  })
  return response.data.audio
}

// 配置
export async function getConfig(): Promise<AppConfig> {
  const response = await api.get(API_PATHS.CONFIG)
  return mapConfig(response.data)
}

export async function updateConfig(payload: ConfigUpdatePayload): Promise<AppConfig> {
  const response = await api.put(API_PATHS.CONFIG, buildConfigUpdateBody(payload))
  return mapConfig(response.data)
}

export async function testConfig(payload: ConfigUpdatePayload): Promise<ConfigTestResult> {
  const response = await api.post(API_PATHS.CONFIG_TEST, buildConfigTestBody(payload))
  return mapTestResult(response.data)
}
