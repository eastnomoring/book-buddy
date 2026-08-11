import type { ChatMessage } from '@book-buddy/core'
import type { ToolEvent } from '../../platform'

/** 展示层消息：在 core ChatMessage 上附加工具事件（T1 MCP 代码执行过程展示） */
export interface UiMessage extends ChatMessage {
  toolEvents?: ToolEvent[]
}
