<script setup lang="ts">
import { computed } from 'vue'
import { renderRichText } from '../../utils/render'
import type { UiMessage } from './types'

const props = withDefaults(
  defineProps<{
    msg: UiMessage
    isLoading: boolean
    isLast: boolean
    /** C4：长工具输出默认折叠，点「展开」后记住 id */
    expandedToolIds: Set<string>
    /** 幽灵加载气泡（尚未插入 assistant 消息时）：强制打字点，不带 aria 播报 */
    forceTyping?: boolean
  }>(),
  { forceTyping: false },
)

const emit = defineEmits<{
  toggleToolPreview: [id: string]
}>()

const PREVIEW_COLLAPSE_CHARS = 280

const TOOL_LABELS: Record<string, string> = {
  run_python: '代码执行',
  create_flashcard: '生成卡片',
  save_note: '保存笔记',
}

function toolLabel(name: string): string {
  return TOOL_LABELS[name] || name
}

function isPreviewLong(preview: string | undefined): boolean {
  return !!preview && preview.length > PREVIEW_COLLAPSE_CHARS
}

function isToolExpanded(id: string): boolean {
  return props.expandedToolIds.has(id)
}

/** 流式已插入空 assistant 气泡时，用气泡内打字点代替「幽灵」加载气泡 */
const showInlineTyping = computed(() => {
  const msg = props.msg
  if (!props.isLoading) return false
  if (!props.isLast) return false
  if (msg.role !== 'assistant') return false
  return !msg.content && !(msg.toolEvents && msg.toolEvents.length)
})

const showTyping = computed(() => props.forceTyping || showInlineTyping.value)
</script>

<template>
  <div class="bubble" :class="msg.role">
    <span class="avatar" aria-hidden="true">{{ msg.role === 'user' ? '你' : '读' }}</span>
    <div class="bubble-col">
      <div class="bubble-label">{{ msg.role === 'user' ? '你' : '伴读' }}</div>
      <div v-if="msg.toolEvents?.length" class="tool-events">
        <div
          v-for="ev in msg.toolEvents"
          :key="ev.id"
          class="tool-event"
          :class="{
            running: ev.type === 'tool_call',
            failed: ev.type === 'tool_result' && !ev.ok,
          }"
        >
          <div class="tool-head">
            <svg class="tool-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M8 4h3v4H8V4Zm5 0h3v6h-3V4ZM8 10h3v10H8V10Zm5 8h3v2h-3v-2Zm0-6h3v4h-3v-4Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
            </svg>
            <span class="tool-name">{{ toolLabel(ev.name) }}</span>
            <span class="tool-id" :title="ev.name">{{ ev.name }}</span>
            <span class="tool-status">
              {{ ev.type === 'tool_call' ? '运行中…' : ev.ok ? '完成' : '失败' }}
            </span>
          </div>
          <div
            v-if="ev.type === 'tool_result' && ev.preview"
            class="tool-preview-wrap"
          >
            <pre
              class="tool-preview"
              :class="{ collapsed: isPreviewLong(ev.preview) && !isToolExpanded(ev.id) }"
            >{{ ev.preview }}</pre>
            <button
              v-if="isPreviewLong(ev.preview)"
              type="button"
              class="tool-toggle"
              @click="emit('toggleToolPreview', ev.id)"
            >
              {{ isToolExpanded(ev.id) ? '收起' : '展开全部' }}
            </button>
          </div>
          <div
            v-if="ev.type === 'tool_result' && ev.images?.length"
            class="tool-images"
          >
            <img
              v-for="(img, imgIdx) in ev.images"
              :key="`${ev.id}-${imgIdx}`"
              class="tool-image"
              :src="`data:${img.mediaType};base64,${img.base64}`"
              :alt="`${ev.name} 输出图 ${imgIdx + 1}`"
            />
          </div>
        </div>
      </div>
      <div
        v-if="showTyping"
        class="bubble-body typing-body"
        :aria-live="showInlineTyping ? 'polite' : undefined"
        :aria-label="showInlineTyping ? '正在生成' : undefined"
      >
        <div class="typing">
          <span></span><span></span><span></span>
        </div>
      </div>
      <div
        v-else-if="msg.content"
        class="bubble-body"
        v-html="renderRichText(msg.content)"
      ></div>
    </div>
  </div>
</template>

<style scoped>
.bubble {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  max-width: min(88%, 42rem);
  animation: rise-in 0.35s var(--ease);
}

.bubble.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.bubble.assistant {
  align-self: flex-start;
}

.avatar {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 0.7rem;
  font-weight: 600;
  margin-top: 0.1rem;
  user-select: none;
}

.bubble.user .avatar {
  background: var(--user-bubble);
  color: #e8eef2;
  box-shadow: 0 2px 6px rgba(21, 32, 40, 0.25);
}

.bubble.assistant .avatar {
  background: var(--accent-gradient);
  color: #f2fffa;
  box-shadow: 0 2px 6px rgba(26, 107, 92, 0.3);
}

.bubble-col {
  min-width: 0;
}

.bubble-label {
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 0.28rem;
  padding: 0 0.15rem;
}

.bubble.user .bubble-label {
  text-align: right;
}

.bubble-body {
  padding: 0.85rem 1rem;
  border-radius: 14px;
  line-height: 1.65;
  word-break: break-word;
}

.tool-events {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin-bottom: 0.35rem;
}

.tool-event {
  padding: 0.4rem 0.65rem;
  border: 1px solid rgba(26, 107, 92, 0.2);
  border-radius: 10px;
  background: rgba(26, 107, 92, 0.06);
  font-size: 0.78rem;
}

.tool-event.running {
  border-color: rgba(26, 107, 92, 0.35);
}

.tool-event.running .tool-status {
  animation: pulse-soft 1.4s ease-in-out infinite;
}

.tool-event.failed {
  border-color: rgba(180, 35, 24, 0.3);
  background: rgba(180, 35, 24, 0.06);
}

.tool-head {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.tool-icon {
  color: var(--accent, #1a6b5c);
}

.tool-name {
  font-weight: 500;
  color: var(--accent, #1a6b5c);
}

.tool-id {
  color: var(--muted);
  font-family: var(--font-mono);
  font-size: 0.65rem;
  opacity: 0.75;
}

.tool-status {
  margin-left: auto;
  color: #6b7884;
  font-size: 0.72rem;
}

.tool-event.failed .tool-name,
.tool-event.failed .tool-icon {
  color: #b42318;
}

.tool-preview-wrap {
  margin-top: 0.35rem;
}

.tool-preview {
  margin: 0;
  padding: 0.4rem 0.5rem;
  border-radius: 6px;
  background: rgba(21, 32, 40, 0.05);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 14rem;
  overflow-y: auto;
}

.tool-preview.collapsed {
  max-height: 4.8rem;
  overflow: hidden;
  mask-image: linear-gradient(to bottom, #000 55%, transparent 100%);
}

.tool-toggle {
  display: inline-flex;
  margin-top: 0.25rem;
  padding: 0.15rem 0.45rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--accent);
  font-family: var(--font-body);
  font-size: 0.72rem;
  cursor: pointer;
}

.tool-toggle:hover {
  background: var(--accent-soft);
}

.typing-body {
  display: flex;
  align-items: center;
  min-height: 2.6rem;
}

.tool-images {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-top: 0.45rem;
}

.tool-image {
  display: block;
  width: 100%;
  max-width: 28rem;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: #fff;
}

.bubble.user .bubble-body {
  background: linear-gradient(150deg, #1d2b35 0%, var(--user-bubble) 70%);
  color: #f4f7f8;
  border-bottom-right-radius: 4px;
  box-shadow: 0 6px 16px rgba(21, 32, 40, 0.18);
}

.bubble.assistant .bubble-body {
  background: var(--assistant-bubble);
  border: 1px solid var(--line);
  border-bottom-left-radius: 4px;
  box-shadow: 0 4px 14px rgba(21, 32, 40, 0.05);
}

.bubble-body :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.88em;
  padding: 0.1em 0.3em;
  border-radius: 4px;
  background: rgba(21, 32, 40, 0.06);
}

.bubble.user .bubble-body :deep(code) {
  background: rgba(255, 255, 255, 0.12);
}

.typing {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0.95rem 1rem;
  border-radius: 14px;
  border-bottom-left-radius: 4px;
  border: 1px solid var(--line);
  background: var(--assistant-bubble);
  box-shadow: 0 4px 14px rgba(21, 32, 40, 0.05);
}

.typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  animation: typing-dot 1.2s ease-in-out infinite;
}

.typing span:nth-child(2) { animation-delay: 0.15s; }
.typing span:nth-child(3) { animation-delay: 0.3s; }

@keyframes typing-dot {
  0%, 100% { opacity: 0.35; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-3px); }
}
</style>
