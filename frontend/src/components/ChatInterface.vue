<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { sendChat, streamChat, type ChatMessage } from '../api/client'

const props = defineProps<{
  bookId?: string | null
  image?: string | null
}>()

const emit = defineEmits<{
  clearImage: []
}>()

const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)

// 监听图片变化，自动添加提示
watch(() => props.image, (newImage) => {
  if (newImage) {
    messages.value.push({
      role: 'user',
      content: '📷 已拍摄书页图片',
    })
  }
})

// 发送消息
async function sendMessage() {
  const text = inputText.value.trim()
  if (!text && !props.image) return
  
  isLoading.value = true
  error.value = null
  
  // 添加用户消息
  const userMessage: ChatMessage = {
    role: 'user',
    content: text || '请解释这张图片的内容',
  }
  messages.value.push(userMessage)
  inputText.value = ''
  
  // 滚动到底部
  await nextTick()
  scrollToBottom()
  
  try {
    // 准备请求
    const history = messages.value.slice(0, -1).map(m => ({
      role: m.role,
      content: m.content,
    }))
    
    // 使用流式响应
    let assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
    }
    messages.value.push(assistantMessage)
    
    const stream = streamChat({
      text,
      image: props.image || undefined,
      bookId: props.bookId || undefined,
      history,
    })
    
    for await (const chunk of stream) {
      assistantMessage.content += chunk
      scrollToBottom()
    }
    
    // 清除已发送的图片
    if (props.image) {
      emit('clearImage')
    }
    
  } catch (e) {
    error.value = '发送失败，请重试'
    console.error(e)
    // 移除失败的 assistant 消息
    messages.value = messages.value.slice(0, -1)
  } finally {
    isLoading.value = false
  }
}

// 语音输入（占位）
function startVoiceInput() {
  alert('语音输入功能开发中...')
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 简单的 Markdown 渲染（实际应用中应使用 marked 库）
function renderMarkdown(text: string): string {
  // 简单处理：换行转 <br>
  return text
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
}
</script>

<template>
  <div class="chat-interface card">
    <div class="chat-header">
      <h3>💬 对话</h3>
      <span v-if="bookId" class="context-badge">
        📖 已关联书籍
      </span>
    </div>

    <div ref="messagesContainer" class="messages">
      <div v-if="messages.length === 0" class="empty-state">
        <p>👋 欢迎使用 Book Buddy！</p>
        <p class="hint">拍照或输入问题开始学习</p>
      </div>

      <div 
        v-for="(msg, idx) in messages" 
        :key="idx"
        class="message"
        :class="msg.role"
      >
        <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
      </div>

      <div v-if="isLoading && messages[messages.length - 1]?.role !== 'assistant'" class="message assistant">
        <div class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div class="input-area">
      <button 
        @click="startVoiceInput" 
        class="voice-btn"
        :disabled="isLoading"
        title="语音输入"
      >
        🎤
      </button>
      
      <input
        v-model="inputText"
        @keyup.enter="sendMessage"
        :disabled="isLoading"
        placeholder="输入问题..."
        class="text-input"
      />
      
      <button 
        @click="sendMessage" 
        class="send-btn"
        :disabled="isLoading || (!inputText.trim() && !image)"
      >
        {{ isLoading ? '...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border);
}

.chat-header h3 {
  margin: 0;
  font-size: 1rem;
}

.context-badge {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  background: #e0f2fe;
  color: #0369a1;
  border-radius: 4px;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.hint {
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.message {
  max-width: 85%;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  line-height: 1.5;
}

.message.user {
  align-self: flex-end;
  background: var(--primary);
  color: white;
}

.message.assistant {
  align-self: flex-start;
  background: #f3f4f6;
}

.message-content {
  white-space: pre-wrap;
}

.typing-indicator {
  display: flex;
  gap: 4px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #9ca3af;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.16s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.32s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.error-message {
  padding: 0.75rem;
  background: #fee;
  color: var(--error);
  border-radius: 6px;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.input-area {
  display: flex;
  gap: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
}

.text-input {
  flex: 1;
}

.voice-btn,
.send-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
}

.voice-btn {
  background: #f3f4f6;
}

.voice-btn:hover:not(:disabled) {
  background: #e5e7eb;
}

.send-btn {
  background: var(--primary);
  color: white;
}

.send-btn:hover:not(:disabled) {
  background: var(--primary-light);
}

.send-btn:disabled,
.voice-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>