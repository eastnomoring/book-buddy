<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { getConfig } from '../api/client'
import { chatStream } from '../platform'
import { SentenceStreamer, type ChatMessage } from '@book-buddy/core'
import { TTSPlayer } from '../utils/tts'
import ChatHeader from './chat/ChatHeader.vue'
import MessageItem from './chat/MessageItem.vue'
import ChatComposer from './chat/ChatComposer.vue'
import { useVoiceInput } from './chat/useVoiceInput'
import type { UiMessage } from './chat/types'

const props = defineProps<{
  bookId?: string | null
  image?: string | null
  pageNumber?: number
}>()

const emit = defineEmits<{
  clearImage: []
}>()

const messages = ref<UiMessage[]>([])
const inputText = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)
const hasPendingImage = ref(false)
/** C4：长工具输出默认折叠，点「展开」后记住 id */
const expandedToolIds = ref<Set<string>>(new Set())

/** 幽灵加载气泡（尚未插入 assistant 消息时）的占位消息 */
const ghostMessage: UiMessage = { role: 'assistant', content: '' }

function toggleToolPreview(id: string): void {
  const next = new Set(expandedToolIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedToolIds.value = next
}

// 语音状态
const voiceConfigured = ref(false)   // 后端已配 DashScope key → 服务端 ASR/TTS
const speakerOn = ref(true)
let ttsPlayer: TTSPlayer | null = null

const { isRecording, isTranscribing, toggleVoiceInput, cancel: cancelVoice } = useVoiceInput({
  voiceConfigured,
  onError: (message) => { error.value = message },
  onInterim: (text) => { inputText.value = text },
  onTranscribed: async (text) => {
    inputText.value = text
    await sendMessage()
  },
})

function handleToggleVoice() {
  error.value = null
  void toggleVoiceInput()
}

onMounted(async () => {
  try {
    const cfg = await getConfig()
    voiceConfigured.value = cfg.voiceConfigured
  } catch (e) {
    console.error('加载配置失败', e)
  }
})

watch(() => props.image, (newImage) => {
  hasPendingImage.value = !!newImage
})

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

  // 新一轮回答：打断上一段朗读
  // Z4：有服务端语音 key 时走 chat 流内 type=audio（省每句 HTTP）；否则回退前端按句合成
  ttsPlayer?.stop()
  const useServerStreamTts = speakerOn.value && voiceConfigured.value
  const player = speakerOn.value ? new TTSPlayer(voiceConfigured.value) : null
  ttsPlayer = player
  const streamer =
    player && !useServerStreamTts
      ? new SentenceStreamer((s) => player.enqueue(s))
      : null

  try {
    const history = messages.value.slice(0, -1).map(m => ({
      role: m.role,
      content: m.content,
    }))

    messages.value.push({
      role: 'assistant',
      content: '',
      toolEvents: [],
    })
    // 必须经由 reactive 数组取引用，直接改本地 plain object 会绕过 proxy、界面不刷新
    const assistantIndex = messages.value.length - 1
    const assistantOf = () => messages.value[assistantIndex] as UiMessage

    const stream = chatStream({
      text: text || undefined,
      image: props.image || undefined,
      bookId: props.bookId || undefined,
      pageNumber: props.pageNumber,
      history,
      enableTts: useServerStreamTts,
    })

    for await (const item of stream) {
      const assistantMessage = assistantOf()
      if (item.type === 'tool') {
        // 工具事件：tool_call 入队，tool_result 按 id 替换同一条（换新数组保证响应式）
        const prev = assistantMessage.toolEvents ?? []
        if (item.event.type === 'tool_call') {
          assistantMessage.toolEvents = [...prev, item.event]
        } else {
          const idx = prev.findIndex((e) => e.id === item.event.id)
          if (idx >= 0) {
            const next = prev.slice()
            next[idx] = item.event
            assistantMessage.toolEvents = next
          } else {
            assistantMessage.toolEvents = [...prev, item.event]
          }
        }
      } else if (item.type === 'audio') {
        player?.enqueueAudio(item.event.base64, item.event.mimeType)
      } else {
        assistantMessage.content += item.text
        streamer?.push(item.text)
      }
      scrollToBottom()
    }
    streamer?.flush() // 冲刷末尾没有句读点的残句

    if (props.image) {
      emit('clearImage')
      hasPendingImage.value = false
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '发送失败，请重试'
    console.error(e)
    player?.stop()
    messages.value = messages.value.slice(0, -1)
  } finally {
    isLoading.value = false
  }
}

function toggleSpeaker() {
  speakerOn.value = !speakerOn.value
  if (!speakerOn.value) ttsPlayer?.stop()
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

onUnmounted(() => {
  cancelVoice()
  ttsPlayer?.stop()
})
</script>

<template>
  <div class="chat">
    <ChatHeader
      :bookId="bookId"
      :pageNumber="pageNumber"
      :hasPendingImage="hasPendingImage"
      :speakerOn="speakerOn"
      @toggleSpeaker="toggleSpeaker"
    />

    <div ref="messagesContainer" class="transcript">
      <div v-if="messages.length === 0" class="empty">
        <svg class="empty-art" viewBox="0 0 120 90" fill="none" aria-hidden="true">
          <rect x="18" y="14" width="84" height="62" rx="7" stroke="currentColor" stroke-width="1.6" opacity="0.5" />
          <path d="M60 26c-5.5-4.5-13-6-20-6-2 0-4 .2-6 .6v44c2-.4 4-.6 6-.6 7 0 14.5 1.5 20 6 5.5-4.5 13-6 20-6 2 0 4 .2 6 .6v-44c-2-.4-4-.6-6-.6-7 0-14.5 1.5-20 6Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
          <path d="M60 26v44" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
          <path d="M42 32h10M42 39h10M68 32h10M68 39h10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" opacity="0.45" />
          <circle cx="98" cy="18" r="5" stroke="currentColor" stroke-width="1.4" opacity="0.55" />
          <path d="M98 15.8v4.4M95.8 18h4.4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" opacity="0.55" />
        </svg>
        <p class="empty-title">从一页书开始</p>
        <p class="empty-copy">拍摄当前页，或直接输入你卡住的地方。</p>
      </div>

      <MessageItem
        v-for="(msg, idx) in messages"
        :key="idx"
        :msg="msg"
        :isLoading="isLoading"
        :isLast="idx === messages.length - 1"
        :expandedToolIds="expandedToolIds"
        @toggleToolPreview="toggleToolPreview"
      />

      <MessageItem
        v-if="isLoading && messages[messages.length - 1]?.role !== 'assistant'"
        :msg="ghostMessage"
        :isLoading="false"
        :isLast="true"
        :expandedToolIds="expandedToolIds"
        forceTyping
      />
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <ChatComposer
      v-model="inputText"
      :isLoading="isLoading"
      :isRecording="isRecording"
      :isTranscribing="isTranscribing"
      :image="image"
      @send="sendMessage"
      @toggleVoice="handleToggleVoice"
      @clearImage="emit('clearImage')"
    />
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

.empty-art {
  width: 7.5rem;
  height: auto;
  margin: 0 auto 1.1rem;
  color: var(--accent);
  opacity: 0.85;
  display: block;
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

.error-banner {
  margin-bottom: 0.65rem;
  padding: 0.65rem 0.8rem;
  border-radius: var(--radius-sm);
  background: var(--error-soft);
  color: var(--error);
  font-size: 0.86rem;
}

@media (max-width: 900px) {
  .chat {
    min-height: 65vh;
    padding: 0.85rem 0.85rem 0.75rem;
  }
}
</style>
