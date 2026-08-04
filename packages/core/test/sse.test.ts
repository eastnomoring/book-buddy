/**
 * SSEParser 契约测试。
 *
 * 钉死「core 如何切 SSE 帧」的假设，与后端 /api/chat/stream 的输出格式
 * 形成对照契约。任一方改动导致格式不一致时，测试必红。
 *
 * 运行：node --import tsx test/sse.test.ts  （或编译后 node test/sse.test.js）
 * 当前用 node:test（Node 18+ 内置，零额外依赖）。
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { SSEParser, type SSEEvent } from '../src/sse.js'

test('单帧：单个 data: 行解析为 delta', () => {
  const p = new SSEParser()
  const events = p.push('data: {"delta":"你好","done":false}\n\n')
  assert.equal(events.length, 1)
  assert.deepEqual(events[0], { delta: '你好', done: false })
})

test('done 帧解析并终止', () => {
  const p = new SSEParser()
  const events = p.push('data: {"delta":"","done":true}\n\n')
  assert.equal(events.length, 1)
  assert.equal(events[0].done, true)
})

test('error 帧携带错误信息', () => {
  const p = new SSEParser()
  const events = p.push('data: {"error":"LLM 调用失败"}\n\n')
  assert.equal(events.length, 1)
  assert.equal(events[0].error, 'LLM 调用失败')
})

test('跨 chunk 的帧：未以 \\n\\n 结尾时不产出，拼接后产出', () => {
  const p = new SSEParser()
  // 第一片：没有结尾空行，不应产出
  assert.equal(p.push('data: {"delta":"碎片"').length, 0)
  // 第二片：补齐结尾
  const events = p.push(',"done":false}\n\n')
  assert.equal(events.length, 1)
  assert.equal(events[0].delta, '碎片')
})

test('多帧连续到达全部解析', () => {
  const p = new SSEParser()
  const input = [
    'data: {"delta":"第一","done":false}\n\n',
    'data: {"delta":"第二","done":false}\n\n',
    'data: {"delta":"","done":true}\n\n',
  ].join('')
  const events = p.push(input)
  assert.equal(events.length, 3)
  assert.equal(events[0].delta, '第一')
  assert.equal(events[1].delta, '第二')
  assert.equal(events[2].done, true)
})

test('中文 delta：UTF-8 解码由传输层负责，parser 只处理字符串', () => {
  const p = new SSEParser()
  // parser 收到的已是字符串（传输层 TextDecoder 解码后）
  const events = p.push('data: {"delta":"概率论 P(X)","done":false}\n\n')
  assert.equal(events[0].delta, '概率论 P(X)')
})

test('无 data: 行的帧被跳过（如纯注释/心跳）', () => {
  const p = new SSEParser()
  // 模拟服务端心跳注释行（标准 SSE 的 `:` 注释）
  const events = p.push(': keepalive\n\n')
  assert.equal(events.length, 0)
})

test('JSON 解析失败的帧被跳过，不抛异常', () => {
  const p = new SSEParser()
  const events = p.push('data: {这不是合法JSON}\n\n')
  assert.equal(events.length, 0)
})

test('空字符串 push 不产出、不报错', () => {
  const p = new SSEParser()
  assert.equal(p.push('').length, 0)
})

// ============ T1: 工具事件（流式 tool loop）============

test('tool_call 事件解析', () => {
  const p = new SSEParser()
  const events = p.push(
    'data: {"type":"tool_call","id":"call_1","name":"run_python","arguments":{"code":"print(1)"}}\n\n',
  )
  assert.equal(events.length, 1)
  const ev = events[0] as any
  assert.equal(ev.type, 'tool_call')
  assert.equal(ev.id, 'call_1')
  assert.equal(ev.name, 'run_python')
  assert.equal(ev.arguments.code, 'print(1)')
})

test('tool_result 事件解析', () => {
  const p = new SSEParser()
  const events = p.push(
    'data: {"type":"tool_result","id":"call_1","name":"run_python","preview":"exit_code: 0","ok":true}\n\n',
  )
  assert.equal(events.length, 1)
  const ev = events[0] as any
  assert.equal(ev.type, 'tool_result')
  assert.equal(ev.ok, true)
  assert.equal(ev.preview, 'exit_code: 0')
})

test('tool_call + delta + tool_result + done 完整序列', () => {
  const p = new SSEParser()
  const input = [
    'data: {"type":"tool_call","id":"call_1","name":"run_python","arguments":{"code":"x"}}\n\n',
    'data: {"delta":"正在运行代码…","done":false}\n\n',
    'data: {"type":"tool_result","id":"call_1","name":"run_python","preview":"stdout","ok":true}\n\n',
    'data: {"delta":"结果如上","done":false}\n\n',
    'data: {"delta":"","done":true}\n\n',
  ].join('')
  const events = p.push(input)
  assert.equal(events.length, 5)
  assert.equal((events[0] as any).type, 'tool_call')
  assert.equal((events[1] as any).delta, '正在运行代码…')
  assert.equal((events[2] as any).type, 'tool_result')
  assert.equal((events[3] as any).delta, '结果如上')
  assert.equal((events[4] as any).done, true)
})

test('未知 type 的事件被原样解析（向后兼容）', () => {
  const p = new SSEParser()
  const events = p.push('data: {"type":"future_event","foo":1}\n\n')
  assert.equal(events.length, 1)
  assert.equal((events[0] as any).type, 'future_event')
})

// ============ Z1: tool_result.images 字段 ============

test('tool_result 带 images 字段解析', () => {
  const p = new SSEParser()
  const events = p.push(
    'data: {"type":"tool_result","id":"call_1","name":"run_python","preview":"ok","ok":true,"images":[{"base64":"iVBOR","mediaType":"image/png"}]}\n\n',
  )
  assert.equal(events.length, 1)
  const ev = events[0] as any
  assert.equal(ev.type, 'tool_result')
  assert.equal(ev.images.length, 1)
  assert.equal(ev.images[0].base64, 'iVBOR')
  assert.equal(ev.images[0].mediaType, 'image/png')
})

test('tool_result 无 images 字段时兼容（缺省即无图）', () => {
  const p = new SSEParser()
  const events = p.push(
    'data: {"type":"tool_result","id":"call_1","name":"run_python","preview":"ok","ok":true}\n\n',
  )
  assert.equal(events.length, 1)
  const ev = events[0] as any
  assert.equal(ev.images, undefined)
})

// ============ Z4: type=audio 事件 ============

test('audio 事件解析', () => {
  const p = new SSEParser()
  const events = p.push(
    'data: {"type":"audio","id":"a1","mimeType":"audio/mpeg","base64":"YWJj","text":"你好。"}\n\n',
  )
  assert.equal(events.length, 1)
  const ev = events[0] as any
  assert.equal(ev.type, 'audio')
  assert.equal(ev.id, 'a1')
  assert.equal(ev.mimeType, 'audio/mpeg')
  assert.equal(ev.base64, 'YWJj')
  assert.equal(ev.text, '你好。')
})
