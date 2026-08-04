/** SSE 帧解析与事件类型定义 */

/** 文本增量事件（无 type 字段，向后兼容） */
export interface SSEDeltaEvent {
  delta: string
  done?: boolean
}

/** 工具调用发起事件 */
export interface SSEToolCallEvent {
  type: 'tool_call'
  id: string
  name: string
  arguments: Record<string, unknown>
}

/** 工具执行结果事件（preview 为截断摘要，≤1KB） */
export interface SSEToolResultEvent {
  type: 'tool_result'
  id: string
  name: string
  preview: string
  ok: boolean
  /** 可选：代码执行生成的图片（向后兼容，无图时省略） */
  images?: SSEImage[]
}

/** Z4：服务端按句 TTS 音频事件（裸 base64，无 data: 前缀） */
export interface SSEAudioEvent {
  type: 'audio'
  id: string
  mimeType: string
  base64: string
  /** 本句朗读文本（已去公式/markdown） */
  text?: string
}

/** 图片产物：裸 base64（无 data: 前缀）+ 媒体类型 */
export interface SSEImage {
  base64: string
  mediaType: string
}

/** 错误事件 */
export interface SSEErrorEvent {
  error: string
}

/** 结束事件 */
export interface SSEDoneEvent {
  delta: ''
  done: true
}

/** 任一事件。解析器返回 SSEEvent[]，调用方按字段区分类型 */
export type SSEEvent =
  | SSEDeltaEvent
  | SSEDoneEvent
  | SSEErrorEvent
  | SSEToolCallEvent
  | SSEToolResultEvent
  | SSEAudioEvent

/**
 * 纯字符串 SSE 帧解析器。
 * 按 `\n\n` 切帧，从每一帧里找出 `data:` 行并尝试 JSON 反序列化。
 * 不依赖任何传输层（fetch / EventSource / wx.request），可在 Web/小程序/桌面端复用。
 * 工具事件通过 type 字段区分；未知 type 的事件会被原样返回（向后兼容）。
 */
export class SSEParser {
  private buffer = ''

  push(chunk: string): SSEEvent[] {
    this.buffer += chunk
    const frames = this.buffer.split('\n\n')
    this.buffer = frames.pop() || ''

    const events: SSEEvent[] = []
    for (const frame of frames) {
      const dataLine = frame
        .split('\n')
        .find((line) => line.startsWith('data: '))
      if (!dataLine) continue

      try {
        const parsed = JSON.parse(dataLine.slice(6)) as SSEEvent
        events.push(parsed)
      } catch {
        // 跳过无法解析的帧，与原有行为一致
        continue
      }
    }
    return events
  }
}
