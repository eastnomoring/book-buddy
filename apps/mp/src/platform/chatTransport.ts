/**
 * 微信小程序端 ChatTransport 实现。
 *
 * 复用 @book-buddy/core 的 SSEParser / buildChatBody / API_PATHS / PlatformError，
 * 只负责传输层：wx.request({ enableChunked: true }) + ArrayBuffer UTF-8 增量解码。
 *
 * T1/C2：工具事件（tool_call / tool_result，含可选 images）经 onToolEvent 回调透出。
 * Z4：type=audio 经 onAudioEvent 透出（服务端按句 TTS）。
 */
import {
  API_PATHS,
  buildChatBody,
  SSEParser,
  PlatformError,
  type ChatRequest,
  type ChatTransport,
  type ChatStreamCallbacks,
  type ChatStreamHandle,
  type SSEAudioEvent,
  type SSEToolCallEvent,
  type SSEToolResultEvent,
} from '@book-buddy/core'
import { getApiBase } from './config'

export type ToolEvent = SSEToolCallEvent | SSEToolResultEvent

/** core 回调尚未含工具事件，小程序端本地扩展（与 web ToolAwareCallbacks 对齐） */
export interface ToolAwareCallbacks extends ChatStreamCallbacks {
  onToolEvent?: (ev: ToolEvent) => void
  onAudioEvent?: (ev: SSEAudioEvent) => void
}

/**
 * UTF-8 增量解码器。
 * 优先使用全局 TextDecoder 的 stream 模式；若运行时不支持（如某些低版本基础库），
 * 则用手工维护的残码缓冲区兜底，保证中文字符跨 chunk 不被切乱。
 */
class Utf8StreamDecoder {
  private leftover = new Uint8Array(0)
  private textDecoder: TextDecoder | undefined

  constructor() {
    if (typeof TextDecoder !== 'undefined') {
      this.textDecoder = new TextDecoder('utf-8')
    }
  }

  push(chunk: ArrayBuffer): string {
    if (this.textDecoder) {
      return this.textDecoder.decode(chunk, { stream: true })
    }
    return this.manualDecode(new Uint8Array(chunk))
  }

  flush(): string {
    if (this.textDecoder) {
      return this.textDecoder.decode(new ArrayBuffer(0), { stream: false })
    }
    this.leftover = new Uint8Array(0)
    return ''
  }

  private manualDecode(data: Uint8Array): string {
    const buf = new Uint8Array(this.leftover.length + data.length)
    buf.set(this.leftover, 0)
    buf.set(data, this.leftover.length)

    let i = 0
    let result = ''
    while (i < buf.length) {
      const b = buf[i]
      let size = 1
      if (b < 0x80) size = 1
      else if ((b & 0xe0) === 0xc0) size = 2
      else if ((b & 0xf0) === 0xe0) size = 3
      else if ((b & 0xf8) === 0xf0) size = 4
      else {
        i++
        continue
      }

      if (i + size > buf.length) {
        this.leftover = buf.slice(i)
        return result
      }

      let cp = 0
      if (size === 1) {
        cp = b
      } else {
        cp = b & ((1 << (7 - size)) - 1)
        for (let k = 1; k < size; k++) {
          const cb = buf[i + k]
          if ((cb & 0xc0) !== 0x80) {
            cp = -1
            break
          }
          cp = (cp << 6) | (cb & 0x3f)
        }
        if (
          cp < 0 ||
          (size === 2 && cp < 0x80) ||
          (size === 3 && cp < 0x800) ||
          (size === 4 && cp < 0x10000)
        ) {
          i += size
          continue
        }
      }

      if (cp <= 0xffff) {
        result += String.fromCharCode(cp)
      } else {
        cp -= 0x10000
        result += String.fromCharCode(0xd800 + (cp >> 10), 0xdc00 + (cp & 0x3ff))
      }
      i += size
    }

    this.leftover = new Uint8Array(0)
    return result
  }
}

export class MpChatTransport implements ChatTransport {
  chatStream(req: ChatRequest, cb: ToolAwareCallbacks): ChatStreamHandle {
    let settled = false
    let aborted = false

    const settle = (type: 'done' | 'error', err?: PlatformError) => {
      if (settled || aborted) return
      settled = true
      if (type === 'error' && err) {
        cb.onError(err)
      } else {
        cb.onDone()
      }
    }

    const task = wx.request({
      url: getApiBase() + API_PATHS.CHAT_STREAM,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
      },
      data: JSON.stringify(buildChatBody(req)),
      enableChunked: true,
      success: (res) => {
        const status = res.statusCode ?? 0
        if (status >= 200 && status < 300) {
          settle('done')
        } else {
          settle('error', new PlatformError(`HTTP ${status}`))
        }
      },
      fail: (err) => {
        settle(
          'error',
          new PlatformError(err.errMsg || 'wx.request failed', err),
        )
      },
    })

    const decoder = new Utf8StreamDecoder()
    const parser = new SSEParser()

    task.onChunkReceived((res) => {
      if (settled || aborted) return
      const text = decoder.push(res.data)
      const events = parser.push(text)
      for (const ev of events) {
        if ('error' in ev && ev.error) {
          settle('error', new PlatformError(String(ev.error), ev.error))
          return
        }
        // T1：工具事件带 type，透传给展示层（含 Z1 images）
        if ('type' in ev && (ev.type === 'tool_call' || ev.type === 'tool_result')) {
          cb.onToolEvent?.(ev as ToolEvent)
          continue
        }
        // Z4：服务端按句 TTS
        if ('type' in ev && ev.type === 'audio') {
          cb.onAudioEvent?.(ev as SSEAudioEvent)
          continue
        }
        if ('delta' in ev && ev.delta) {
          cb.onChunk(ev.delta)
        }
        if ('done' in ev && ev.done) {
          settle('done')
          return
        }
      }
    })

    return {
      abort: () => {
        if (aborted || settled) return
        aborted = true
        try {
          task.abort()
        } catch {
          // ignore
        }
        decoder.flush()
      },
    }
  }
}
