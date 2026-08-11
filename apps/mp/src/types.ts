import type { ChatMessage } from '@book-buddy/core'
import type { ToolEvent } from './platform/chatTransport'

/** 展示层消息：附加工具事件与落盘后的图片路径 */
export interface UiMessage extends ChatMessage {
  toolEvents?: ToolEvent[]
  /** tool_result.images 落盘后的本地路径，按 tool id 索引 */
  toolImagePaths?: Record<string, string[]>
}
