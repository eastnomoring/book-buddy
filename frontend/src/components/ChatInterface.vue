<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { streamChat, type ChatMessage } from '../api/client'

const props = defineProps<{
  bookId?: string | null
  image?: string | null
  pageNumber?: number
}>()

const emit = defineEmits<{
  clearImage: []
}>()

const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)
const hasPendingImage = ref(false)

watch(() => props.image, (newImage) => {
  hasPendingImage.value = !!newImage
})

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderMarkdown(text: string): string {
  const escaped = escapeHtml(text)
  return escaped
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text && !props.image) return

  isLoading.value = true
  error.value = null

  const userMessage: ChatMessage = {
    role: 'user',
    content: text || '请解释这张图片的内容',
  }
  messages.value.push(userMessage)
  inputText.value = ''

  await nextTick()
  scrollToBottom()

  try {
    const history = messages.value.slice(0, -1).map(m => ({
      role: m.role,
      content: m.content,
    }))

    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
    }
    messages.value.push(assistantMessage)

    const stream = streamChat({
      text: text || undefined,
      image: props.image || undefined,
      bookId: props.bookId || undefined,
      pageNumber: props.pageNumber,
      history,
    })

    for await (const chunk of stream) {
      assistantMessage.content += chunk
      scrollToBottom()
    }

    if (props.image) {
      emit('clearImage')
      hasPendingImage.value = false
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '发送失败，请重试'
    console.error(e)
    messages.value = messages.value.slice(0, -1)
  } finally {
    isLoading.value = false
  }
}

function startVoiceInput() {
  alert('语音输入功能开发中...')
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}
</script>

<template>
  <div class="chat">
    <div class="chat-top">
      <div>
        <h2 class="pane-title">问答</h2>
        <p class="pane-sub">结合书页与知识库，按书中符号体系讲解</p>
      </div>
      <div class="status-row">
        <span v-if="bookId" class="status">已关联书籍</span>
        <span v-if="pageNumber" class="status tone">第 {{ pageNumber }} 页</span>
        <span v-if="hasPendingImage" class="status pending">待发送图片</span>
      </div>
    </div>

    <div ref="messagesContainer" class="transcript">
      <div v-if="messages.length === 0" class="empty">
        <p class="empty-title">从一页书开始</p>
        <p class="empty-copy">拍摄当前页，或直接输入你卡住的地方。</p>
      </div>

      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="bubble"
        :class="msg.role"
      >
        <div class="bubble-label">{{ msg.role === 'user' ? '你' : '伴读' }}</div>
        <div class="bubble-body" v-html="renderMarkdown(msg.content)"></div>
      </div>

      <div
        v-if="isLoading && messages[messages.length - 1]?.role !== 'assistant'"
        class="bubble assistant"
      >
        <div class="bubble-label">伴读</div>
        <div class="typing">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <div class="composer">
      <button
        @click="startVoiceInput"
        class="icon-btn"
        :disabled="isLoading"
        title="语音输入"
        aria-label="语音输入"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z" stroke="currentColor" stroke-width="1.6"/>
          <path d="M19 11a7 7 0 0 1-14 0M12 18v3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
        </svg>
      </button>

      <input
        v-model="inputText"
        @keyup.enter="sendMessage"
        :disabled="isLoading"
        placeholder="这一页哪里卡住了？"
        class="composer-input"
      />

      <button
        @click="sendMessage"
        class="btn btn-primary send"
        :disabled="isLoading || (!inputText.trim() && !image)"
      >
        {{ isLoading ? '生成中' : '发送' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 520px;
  padding: 1.15rem 1.15rem 1rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
  backdrop-filter: blur(10px);
  box-shadow: var(--shadow-soft);
}

.chat-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding-bottom: 0.95rem;
  border-bottom: 1px solid var(--line);
}

.pane-title {
  font-family: var(--font-display);
  font-size: 1.45rem;
  font-weight: 400;
  line-height: 1.1;
}

.pane-sub {
  margin-top: 0.3rem;
  font-size: 0.82rem;
  color: var(--muted);
}

.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  justify-content: flex-end;
}

.status {
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  padding: 0.28rem 0.5rem;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent-deep);
}

.status.tone {
  background: rgba(21, 32, 40, 0.06);
  color: var(--ink-soft);
}

.status.pending {
  background: var(--warn-soft);
  color: var(--warn);
}

.transcript {
  flex: 1;
  overflow-y: auto;
  padding: 1.1rem 0.15rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.empty {
  margin: auto;
  text-align: center;
  max-width: 18rem;
  animation: rise-in 0.6s var(--ease);
}

.empty-title {
  font-family: var(--font-display);
  font-size: 1.55rem;
  margin-bottom: 0.4rem;
}

.empty-copy {
  color: var(--muted);
  font-size: 0.92rem;
}

.bubble {
  max-width: min(88%, 42rem);
  animation: rise-in 0.35s var(--ease);
}

.bubble.user {
  align-self: flex-end;
}

.bubble.assistant {
  align-self: flex-start;
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
  border-radius: 12px;
  line-height: 1.65;
  word-break: break-word;
}

.bubble.user .bubble-body {
  background: var(--user-bubble);
  color: #f4f7f8;
  border-bottom-right-radius: 4px;
}

.bubble.assistant .bubble-body {
  background: var(--assistant-bubble);
  border: 1px solid var(--line);
  border-bottom-left-radius: 4px;
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
  gap: 5px;
  padding: 0.95rem 1rem;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: var(--assistant-bubble);
}

.typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--muted);
  animation: pulse-soft 1.2s ease-in-out infinite;
}

.typing span:nth-child(2) { animation-delay: 0.15s; }
.typing span:nth-child(3) { animation-delay: 0.3s; }

.composer {
  display: flex;
  gap: 0.55rem;
  align-items: center;
  padding-top: 0.85rem;
  border-top: 1px solid var(--line);
}

.composer-input {
  flex: 1;
}

.icon-btn {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  color: var(--ink-soft);
  background: rgba(255, 255, 255, 0.7);
  transition: background 0.2s var(--ease), border-color 0.2s var(--ease);
}

.icon-btn:hover:not(:disabled) {
  border-color: var(--line-strong);
  background: #fff;
}

.icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.send {
  min-width: 5.2rem;
}

.error-banner {
  margin-bottom: 0.65rem;
  padding: 0.65rem 0.8rem;
  border-radius: var(--radius-sm);
  background: var(--error-soft);
  color: var(--error);
  font-size: 0.86rem;
}
</style>
