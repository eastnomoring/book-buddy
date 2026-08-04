/**
 * 请求体映射契约测试。
 *
 * 钉死 core 的 buildChatBody / buildConfigUpdateBody / buildConfigTestBody
 * 输出的 snake_case 字段名，与后端 Pydantic 请求模型的字段名一致。
 *
 * 后端字段名见 backend/app/models/chat.py (ChatRequest) 和
 * backend/app/models/config.py (ConfigUpdate / ConfigTestRequest)。
 * 任一方改名时，本测试与后端测试形成对照，必有一边红。
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  buildChatBody,
  buildConfigUpdateBody,
  buildConfigTestBody,
  API_PATHS,
} from '../src/api.js'
import type { ChatRequest, ConfigUpdatePayload } from '../src/types.js'

test('buildChatBody: camelCase 入参映射为后端 snake_case 字段', () => {
  const req: ChatRequest = {
    text: '为什么？',
    image: 'base64img',
    mediaType: 'image/png',
    audio: 'base64audio',
    bookId: 'book-123',
    pageNumber: 47,
    history: [{ role: 'user', content: '上文' }],
    enableTts: true,
  }
  const body = buildChatBody(req)

  // 与 backend ChatRequest 字段逐一对照
  assert.equal(body.text, '为什么？')
  assert.equal(body.image, 'base64img')
  assert.equal(body.media_type, 'image/png', 'mediaType → media_type')
  assert.equal(body.audio, 'base64audio')
  assert.equal(body.book_id, 'book-123', 'bookId → book_id')
  assert.equal(body.page_number, 47, 'pageNumber → page_number')
  assert.deepEqual(body.history, [{ role: 'user', content: '上文' }])
  assert.equal(body.enable_tts, true, 'enableTts → enable_tts')
})

test('buildChatBody: 空值字段保留为 undefined（后端可选字段）', () => {
  const body = buildChatBody({ text: '只问一句' })
  assert.equal(body.text, '只问一句')
  assert.equal(body.image, undefined)
  assert.equal(body.audio, undefined)
  assert.equal(body.book_id, undefined)
  assert.equal(body.page_number, undefined)
  assert.deepEqual(body.history, undefined)
})

test('buildConfigUpdateBody: voice_api_key 独立字段（与 LLM provider 解耦）', () => {
  const payload: ConfigUpdatePayload = {
    provider: 'openai',
    apiKey: 'sk-llm',
    baseUrl: 'https://example.com',
    model: 'glm-4.6v',
    voiceApiKey: 'sk-voice',
  }
  const body = buildConfigUpdateBody(payload)

  // 与 backend ConfigUpdate 字段对照
  assert.equal(body.provider, 'openai')
  assert.equal(body.api_key, 'sk-llm', 'apiKey → api_key')
  assert.equal(body.base_url, 'https://example.com', 'baseUrl → base_url')
  assert.equal(body.model, 'glm-4.6v')
  assert.equal(body.voice_api_key, 'sk-voice', 'voiceApiKey → voice_api_key')
})

test('buildConfigTestBody: 不含 voice_api_key（测试连接只验 LLM）', () => {
  const body = buildConfigTestBody({
    provider: 'qwen',
    apiKey: 'sk-test',
  })
  assert.equal(body.provider, 'qwen')
  assert.equal(body.api_key, 'sk-test')
  assert.equal(body.base_url, undefined)
  assert.equal(body.model, undefined)
  assert.equal('voice_api_key' in body, false, '测试连接不该带语音 key')
})

test('API_PATHS: 路径常量与后端路由 prefix+path 一致', () => {
  // 后端 main.py: app.include_router(chat.router, prefix="/api")
  // chat.py: @router.post("/chat/stream") → 完整 /api/chat/stream
  assert.equal(API_PATHS.CHAT, '/chat')
  assert.equal(API_PATHS.CHAT_STREAM, '/chat/stream')
  assert.equal(API_PATHS.BOOKS, '/books')
  assert.equal(API_PATHS.BOOKS_UPLOAD, '/books/upload')
  assert.equal(API_PATHS.VOICE_TRANSCRIBE, '/voice/transcribe')
  assert.equal(API_PATHS.VOICE_SYNTHESIZE, '/voice/synthesize')
  assert.equal(API_PATHS.CONFIG, '/config')
  assert.equal(API_PATHS.CONFIG_TEST, '/config/test')
})
