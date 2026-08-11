/**
 * 响应体映射契约测试。
 *
 * 钉死 core 的 mapChatResponse / mapBookInfo / mapUploadResult /
 * mapConfig / mapTestResult 把后端 snake_case JSON 转成前端 camelCase
 * 模型的行为：字段重命名、缺省兜底、类型转换。
 *
 * 与 test/api.test.ts（请求体方向）形成双向对照：后端响应模型改名时，
 * 本测试必红。
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  mapChatResponse,
  mapBookInfo,
  mapUploadResult,
  mapConfig,
  mapTestResult,
} from '../src/api.js'

// ============ mapChatResponse ============

test('mapChatResponse: snake_case 响应映射为 camelCase 模型', () => {
  const res = mapChatResponse({
    text: '这是回答',
    audio: 'YXVkaW8=',
    sources: ['第 3 章', '附录 A'],
    page_references: [47, 48],
  })
  assert.equal(res.text, '这是回答')
  assert.equal(res.audio, 'YXVkaW8=')
  assert.deepEqual(res.sources, ['第 3 章', '附录 A'])
  assert.deepEqual(res.pageReferences, [47, 48], 'page_references → pageReferences')
})

test('mapChatResponse: pageReferences 兼容 camelCase，snake_case 优先', () => {
  const camelOnly = mapChatResponse({ text: '答', pageReferences: [1, 2] })
  assert.deepEqual(camelOnly.pageReferences, [1, 2])

  const both = mapChatResponse({ text: '答', page_references: [9], pageReferences: [1] })
  assert.deepEqual(both.pageReferences, [9], '两种命名并存时以后端 snake_case 为准')
})

test('mapChatResponse: 缺省字段兜底', () => {
  const res = mapChatResponse({})
  assert.equal(res.text, '')
  assert.equal(res.audio, undefined)
  assert.deepEqual(res.sources, [])
  assert.deepEqual(res.pageReferences, [])
})

test('mapChatResponse: text 强制 String，audio 空串视为无音频', () => {
  const res = mapChatResponse({ text: 42, audio: '' })
  assert.equal(res.text, '42')
  assert.equal(res.audio, undefined, '空字符串 audio 按无音频处理')
})

// ============ mapBookInfo ============

test('mapBookInfo: snake_case 响应映射（含 chapters）', () => {
  const book = mapBookInfo({
    id: 'book-1',
    title: '线性代数',
    author: '某出版社',
    total_pages: 320,
    chapters: [
      { title: '行列式', start_page: 1 },
      { title: '矩阵', start_page: 45 },
    ],
  })
  assert.equal(book.id, 'book-1')
  assert.equal(book.title, '线性代数')
  assert.equal(book.author, '某出版社')
  assert.equal(book.totalPages, 320, 'total_pages → totalPages')
  assert.deepEqual(book.chapters, [
    { title: '行列式', startPage: 1 },
    { title: '矩阵', startPage: 45 },
  ])
})

test('mapBookInfo: camelCase 命名兜底（totalPages / startPage）', () => {
  const book = mapBookInfo({
    id: 'b2',
    title: '概率论',
    totalPages: 280,
    chapters: [{ title: '随机变量', startPage: 60 }],
  })
  assert.equal(book.totalPages, 280)
  assert.deepEqual(book.chapters, [{ title: '随机变量', startPage: 60 }])
})

test('mapBookInfo: 缺省字段兜底', () => {
  const book = mapBookInfo({})
  assert.equal(book.id, '')
  assert.equal(book.title, '')
  assert.equal(book.author, undefined, 'author 缺省为 undefined 而非空串')
  assert.equal(book.totalPages, 0)
  assert.deepEqual(book.chapters, [])
})

test('mapBookInfo: 数字字段经 Number 转换，author 空串视为缺省', () => {
  const book = mapBookInfo({
    id: 'b3',
    title: '习题集',
    author: '',
    total_pages: '120',
    chapters: [{ title: '第一章', start_page: '7' }],
  })
  assert.equal(book.totalPages, 120)
  assert.equal(book.author, undefined)
  assert.deepEqual(book.chapters, [{ title: '第一章', startPage: 7 }])
})

// ============ mapUploadResult ============

test('mapUploadResult: 正常映射', () => {
  const res = mapUploadResult({ id: 'b9', title: '新书', message: '上传成功，解析中' })
  assert.deepEqual(res, { id: 'b9', title: '新书', message: '上传成功，解析中' })
})

test('mapUploadResult: 缺省字段兜底为空串', () => {
  assert.deepEqual(mapUploadResult({}), { id: '', title: '', message: '' })
})

// ============ mapConfig ============

test('mapConfig: snake_case 响应映射为 camelCase 模型', () => {
  const cfg = mapConfig({
    provider: 'qwen',
    base_url: 'https://dashscope.example.com',
    model: 'qwen-vl-max',
    api_key_masked: 'sk-****llm',
    configured: true,
    voice_configured: true,
    voice_api_key_masked: 'sk-****voice',
  })
  assert.equal(cfg.provider, 'qwen')
  assert.equal(cfg.baseUrl, 'https://dashscope.example.com', 'base_url → baseUrl')
  assert.equal(cfg.model, 'qwen-vl-max')
  assert.equal(cfg.apiKeyMasked, 'sk-****llm', 'api_key_masked → apiKeyMasked')
  assert.equal(cfg.configured, true)
  assert.equal(cfg.voiceConfigured, true, 'voice_configured → voiceConfigured')
  assert.equal(cfg.voiceApiKeyMasked, 'sk-****voice', 'voice_api_key_masked → voiceApiKeyMasked')
})

test('mapConfig: 缺省字段兜底（provider 默认 openai）', () => {
  const cfg = mapConfig({})
  assert.equal(cfg.provider, 'openai')
  assert.equal(cfg.baseUrl, undefined)
  assert.equal(cfg.model, '')
  assert.equal(cfg.apiKeyMasked, '')
  assert.equal(cfg.configured, false)
  assert.equal(cfg.voiceConfigured, false)
  assert.equal(cfg.voiceApiKeyMasked, '')
})

test('mapConfig: base_url 空串视为未配置，布尔字段做真值转换', () => {
  const cfg = mapConfig({ base_url: '', configured: 1, voice_configured: 0 })
  assert.equal(cfg.baseUrl, undefined)
  assert.equal(cfg.configured, true)
  assert.equal(cfg.voiceConfigured, false)
})

// ============ mapTestResult ============

test('mapTestResult: 正常映射', () => {
  assert.deepEqual(mapTestResult({ ok: true, message: '连接成功' }), {
    ok: true,
    message: '连接成功',
  })
})

test('mapTestResult: 缺省兜底与真值转换', () => {
  assert.deepEqual(mapTestResult({}), { ok: false, message: '' })
  assert.deepEqual(mapTestResult({ ok: 1, message: '非布尔 ok' }), {
    ok: true,
    message: '非布尔 ok',
  })
})
