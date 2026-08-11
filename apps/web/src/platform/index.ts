/**
 * Web 端平台能力实现：把现有的 fetch + getUserMedia + Audio 实现
 * 收拢为 @book-buddy/core 的 ChatTransport / PhotoCapture / AudioRecorder / AudioPlayer 接口实现。
 *
 * Z2 任务：行为零变化，只把散落的函数收拢为接口实现类，组件改从接口导入。
 */
import {
  buildChatBody,
  API_PATHS,
  PlatformError,
  SSEParser,
  type ChatRequest,
  type ChatStreamCallbacks,
  type ChatStreamHandle,
  type PhotoResult,
  type AudioRecordResult,
  type SSEToolCallEvent,
  type SSEToolResultEvent,
  type SSEAudioEvent,
} from '@book-buddy/core'
import { synthesizeVoice, transcribeVoice } from '../api/client'

/** 工具事件（tool_call / tool_result）。T1 协议：文本增量不带 type，工具事件带 type */
export type ToolEvent = SSEToolCallEvent | SSEToolResultEvent

/**
 * 扩展回调：core 的 ChatStreamCallbacks 暂未包含工具/音频事件回调，
 * 先在 web 端本地扩展（core 补齐后可删除本接口）。
 */
export interface ToolAwareCallbacks extends ChatStreamCallbacks {
  onToolEvent?: (ev: ToolEvent) => void
  /** Z4：服务端按句 TTS */
  onAudioEvent?: (ev: SSEAudioEvent) => void
}

// ============ ChatTransport ============

const API_BASE = '/api'

/**
 * Web 端流式对话：fetch + ReadableStream + core SSEParser。
 * 把现有 streamChat 的 generator 逻辑包装为回调式 ChatTransport。
 * 帧解析复用 @book-buddy/core 的 SSEParser（按 \n\n 切帧），与小程序端行为一致；
 * abort 通过 AbortController 真正取消 fetch，中止后不再触发任何回调。
 */
class WebChatTransportImpl {
  chatStream(req: ChatRequest, cb: ToolAwareCallbacks): ChatStreamHandle {
    let aborted = false
    const controller = new AbortController()
    const decoder = new TextDecoder()
    const parser = new SSEParser()

    const run = async () => {
      try {
        const response = await fetch(API_BASE + API_PATHS.CHAT_STREAM, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(buildChatBody(req)),
          signal: controller.signal,
        })

        if (!response.ok) {
          cb.onError(new PlatformError(`HTTP ${response.status}`))
          return
        }

        const reader = response.body?.getReader()
        if (!reader) {
          cb.onError(new PlatformError('无响应体'))
          return
        }

        while (true) {
          if (aborted) return
          const { done, value } = await reader.read()
          if (done) break

          const events = parser.push(decoder.decode(value, { stream: true }))
          for (const ev of events) {
            if ('error' in ev && ev.error) {
              cb.onError(new PlatformError(String(ev.error)))
              return
            }
            // T1：工具事件带 type，透传给展示层
            if ('type' in ev && (ev.type === 'tool_call' || ev.type === 'tool_result')) {
              cb.onToolEvent?.(ev as ToolEvent)
              continue
            }
            // Z4：服务端 TTS 音频
            if ('type' in ev && ev.type === 'audio') {
              cb.onAudioEvent?.(ev as SSEAudioEvent)
              continue
            }
            if ('delta' in ev && ev.delta) cb.onChunk(ev.delta)
            if ('done' in ev && ev.done) {
              cb.onDone()
              return
            }
          }
        }
        cb.onDone()
      } catch (e) {
        // 用户主动 abort：fetch/reader 抛 AbortError，静默收尾，不误报 onError
        if (aborted || (e instanceof DOMException && e.name === 'AbortError')) return
        cb.onError(new PlatformError('网络请求失败', e))
      }
    }

    void run()

    return {
      abort: () => {
        if (aborted) return
        aborted = true
        controller.abort()
      },
    }
  }
}

// ============ PhotoCapture ============

/**
 * Web 端拍照：getUserMedia 预览 + canvas 截帧。
 * 注意：此实现假设 CameraCapture.vue 仍负责预览 UI；
 * 这里提供「直接拍照返回 base64」的能力，供组件按需调用。
 * 现有 CameraCapture.vue 的拍照逻辑保持不动（UI 耦合较深），
 * 本类作为接口实现存在，供未来解耦或新组件使用。
 */
class WebPhotoCaptureImpl {
  async capture(): Promise<PhotoResult> {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    })

    try {
      const video = document.createElement('video')
      video.srcObject = stream
      video.muted = true
      await video.play()

      // 等一帧稳定
      await new Promise((r) => setTimeout(r, 200))

      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')
      if (!ctx) throw new PlatformError('无法获取 canvas 上下文')
      ctx.drawImage(video, 0, 0)

      const dataUrl = canvas.toDataURL('image/jpeg', 0.8)
      const base64 = dataUrl.split(',')[1]

      return { base64, mediaType: 'image/jpeg' }
    } finally {
      stream.getTracks().forEach((t) => t.stop())
    }
  }
}

// ============ AudioRecorder ============

/**
 * Web 端录音：getUserMedia + Web Audio，重采样 16kHz 单声道 WAV。
 * 包装现有 utils/audio.ts 的 startRecording，对齐 AudioRecorder 接口。
 */
class WebAudioRecorderImpl {
  private recorder: {
    stop: () => Promise<string>
    cancel: () => void
  } | null = null

  async start(): Promise<void> {
    // 动态 import 避免未使用时也加载录音逻辑
    const { startRecording } = await import('../utils/audio')
    try {
      this.recorder = await startRecording()
    } catch (e) {
      throw new PlatformError('无法访问麦克风，请检查浏览器权限', e)
    }
  }

  async stop(): Promise<AudioRecordResult> {
    const current = this.recorder
    this.recorder = null
    if (!current) throw new PlatformError('未在录音')
    const base64 = await current.stop()
    return { base64, mimeType: 'audio/wav', sampleRate: 16000 }
  }

  cancel(): void {
    this.recorder?.cancel()
    this.recorder = null
  }
}

// ============ AudioPlayer ============

/**
 * Web 端 TTS 播放：HTMLAudioElement。
 * 包装现有 utils/tts.ts 的 playAudio 逻辑。
 */
class WebAudioPlayerImpl {
  private current: HTMLAudioElement | null = null

  async play(base64: string, mimeType: string): Promise<void> {
    this.stop()
    return new Promise((resolve) => {
      const audio = new Audio(`data:${mimeType};base64,${base64}`)
      this.current = audio
      audio.onended = () => resolve()
      audio.onerror = () => resolve()
      audio.play().catch(() => resolve())
    })
  }

  stop(): void {
    this.current?.pause()
    this.current = null
  }
}

// ============ 单例导出 ============

export const webChatTransport = new WebChatTransportImpl()
export const webPhotoCapture = new WebPhotoCaptureImpl()
export const webAudioRecorder = new WebAudioRecorderImpl()
export const webAudioPlayer = new WebAudioPlayerImpl()

// 重新导出底层 API（供 tts.ts SentenceStreamer 等仍需直接调用后端的地方使用）
export { synthesizeVoice, transcribeVoice }

// ============ generator 适配器 ============

/** chatStream 的产生项：文本增量 / 工具事件 / 服务端音频 */
export type ChatStreamItem =
  | { type: 'delta'; text: string }
  | { type: 'tool'; event: ToolEvent }
  | { type: 'audio'; event: SSEAudioEvent }

/**
 * 把回调式 ChatTransport 适配为 AsyncGenerator，供组件用 `for await` 消费。
 * 统一 web 端的流式对话路径走 platform 实现，消除与旧 client.ts generator 的双路径。
 */
export async function* chatStream(req: ChatRequest): AsyncGenerator<ChatStreamItem> {
  const queue: Array<{
    delta?: string
    done?: boolean
    err?: PlatformError
    tool?: ToolEvent
    audio?: SSEAudioEvent
  }> = []
  let resolveWait: (() => void) | null = null

  const wake = () => {
    resolveWait?.()
    resolveWait = null
  }

  const handle = webChatTransport.chatStream(req, {
    onChunk: (delta) => {
      queue.push({ delta })
      wake()
    },
    onDone: () => {
      queue.push({ done: true })
      wake()
    },
    onError: (err) => {
      queue.push({ err })
      wake()
    },
    onToolEvent: (ev) => {
      queue.push({ tool: ev })
      wake()
    },
    onAudioEvent: (ev) => {
      queue.push({ audio: ev })
      wake()
    },
  })

  try {
    while (true) {
      const item = queue.shift()
      if (item) {
        if (item.err) throw item.err
        if (item.done) return
        if (item.tool) yield { type: 'tool', event: item.tool }
        else if (item.audio) yield { type: 'audio', event: item.audio }
        else if (item.delta) yield { type: 'delta', text: item.delta }
      } else {
        await new Promise<void>((r) => {
          resolveWait = r
        })
      }
    }
  } finally {
    handle.abort()
  }
}
