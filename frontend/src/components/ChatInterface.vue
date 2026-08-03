<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { streamChat, transcribeVoice, getConfig, type ChatMessage } from '../api/client'
import { renderRichText } from '../utils/render'
import { startRecording, type VoiceRecorder } from '../utils/audio'
import { SentenceStreamer, TTSPlayer } from '../utils/tts'

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

// 语音状态
const voiceConfigured = ref(false)   // 后端已配 DashScope key → 服务端 ASR/TTS
const isRecording = ref(false)
const isTranscribing = ref(false)
const speakerOn = ref(true)
let recorder: VoiceRecorder | null = null
let recognition: { stop: () => void } | null = null
let ttsPlayer: TTSPlayer | null = null

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

  // 新一轮回答：打断上一段朗读，按句流水朗读本轮回答
  ttsPlayer?.stop()
  const player = speakerOn.value ? new TTSPlayer(voiceConfigured.value) : null
  ttsPlayer = player
  const streamer = player ? new SentenceStreamer((s) => player.enqueue(s)) : null

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
      streamer?.push(chunk)
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

/** 麦克风按钮：点一下开始录音，再点一下结束并转写发送 */
async function toggleVoiceInput() {
  if (isRecording.value) {
    await stopVoiceInput()
    return
  }

  error.value = null
  if (voiceConfigured.value) {
    // 服务端 ASR：WAV 录音 → /voice/transcribe
    try {
      recorder = await startRecording()
      isRecording.value = true
    } catch (e) {
      console.error(e)
      error.value = '无法访问麦克风，请检查浏览器权限'
    }
  } else {
    // 无 key 兜底：浏览器自带语音识别
    startWebSpeech()
  }
}

async function stopVoiceInput() {
  if (!voiceConfigured.value) {
    recognition?.stop() // onend 回调里处理发送
    return
  }

  const current = recorder
  recorder = null
  isRecording.value = false
  if (!current) return

  isTranscribing.value = true
  try {
    const wavBase64 = await current.stop()
    const result = await transcribeVoice(wavBase64, 'wav')
    const text = result.text.trim()
    if (text) {
      inputText.value = text
      await sendMessage()
    }
  } catch (e) {
    console.error(e)
    error.value = e instanceof Error ? e.message : '语音识别失败，请重试'
  } finally {
    isTranscribing.value = false
  }
}

/** 浏览器 Web Speech 兜底：边说边出字，说完自动发送 */
function startWebSpeech() {
  const w = window as unknown as Record<string, unknown>
  const SR = (w.SpeechRecognition || w.webkitSpeechRecognition) as (new () => {
    lang: string
    interimResults: boolean
    continuous: boolean
    onresult: (e: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void
    onend: () => void
    onerror: () => void
    start: () => void
    stop: () => void
  }) | undefined

  if (!SR) {
    error.value = '当前浏览器不支持语音识别，请在设置中配置语音 Key'
    return
  }

  const rec = new SR()
  let finalText = ''
  rec.lang = 'zh-CN'
  rec.interimResults = true
  rec.continuous = false
  rec.onresult = (e) => {
    let interim = ''
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript
      if (e.results[i].isFinal) finalText += t
      else interim += t
    }
    inputText.value = finalText + interim
  }
  rec.onend = () => {
    isRecording.value = false
    recognition = null
    if (finalText.trim()) {
      inputText.value = finalText.trim()
      void sendMessage()
    }
  }
  rec.onerror = () => {
    isRecording.value = false
    recognition = null
    error.value = '语音识别失败，请重试'
  }

  recognition = rec
  isRecording.value = true
  rec.start()
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
  recorder?.cancel()
  recognition?.stop()
  ttsPlayer?.stop()
})
</script>

<template>
  <div class="chat">
    <div class="chat-top">
      <div>
        <h2 class="pane-title">问答</h2>
        <p class="pane-sub">结合书页与知识库，按书中符号体系讲解</p>
      </div>
      <div class="status-row">
        <span v-if="bookId" class="status"><i class="dot" aria-hidden="true"></i>已关联书籍</span>
        <span v-if="pageNumber" class="status tone"><i class="dot" aria-hidden="true"></i>第 {{ pageNumber }} 页</span>
        <span v-if="hasPendingImage" class="status pending"><i class="dot" aria-hidden="true"></i>待发送图片</span>
        <button
          type="button"
          class="speaker-btn"
          :class="{ muted: !speakerOn }"
          @click="toggleSpeaker"
          :title="speakerOn ? '关闭朗读' : '开启朗读'"
          :aria-label="speakerOn ? '关闭朗读' : '开启朗读'"
        >
          <svg v-if="speakerOn" width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M11 5 6.5 9H3v6h3.5L11 19V5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
            <path d="M15 9a4 4 0 0 1 0 6M17.5 6.5a7.5 7.5 0 0 1 0 11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </svg>
          <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M11 5 6.5 9H3v6h3.5L11 19V5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
            <path d="m16 9 5 6m0-6-5 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </svg>
        </button>
      </div>
    </div>

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

      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="bubble"
        :class="msg.role"
      >
        <span class="avatar" aria-hidden="true">{{ msg.role === 'user' ? '你' : '读' }}</span>
        <div class="bubble-col">
          <div class="bubble-label">{{ msg.role === 'user' ? '你' : '伴读' }}</div>
          <div class="bubble-body" v-html="renderRichText(msg.content)"></div>
        </div>
      </div>

      <div
        v-if="isLoading && messages[messages.length - 1]?.role !== 'assistant'"
        class="bubble assistant"
      >
        <span class="avatar" aria-hidden="true">读</span>
        <div class="bubble-col">
          <div class="bubble-label">伴读</div>
          <div class="typing">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <div v-if="isRecording || isTranscribing" class="voice-hint" :class="{ recording: isRecording }">
      {{ isRecording ? '录音中…再点一次麦克风结束' : '识别中…' }}
    </div>

    <div v-if="image" class="pending-image">
      <img :src="'data:image/jpeg;base64,' + image" alt="待发送的书页图片" class="pending-thumb" />
      <span class="pending-text">将随下一条消息发送</span>
      <button
        type="button"
        class="pending-remove"
        @click="emit('clearImage')"
        title="移除图片"
        aria-label="移除待发送图片"
      >
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="m6 6 12 12M18 6 6 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
        </svg>
      </button>
    </div>

    <div class="composer">
      <button
        @click="toggleVoiceInput"
        class="icon-btn"
        :class="{ recording: isRecording }"
        :disabled="isLoading || isTranscribing"
        :title="isRecording ? '结束录音' : '语音输入'"
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
        <svg class="send-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M4.5 12 19.5 4.5 13.5 19.5l-2.7-5.4-6.3-2.1Z"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linejoin="round"
          />
          <path d="M10.8 14.1 19.5 4.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
        </svg>
        <span>{{ isLoading ? '生成中' : '发送' }}</span>
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
  display: inline-flex;
  align-items: center;
  gap: 0.32rem;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  padding: 0.3rem 0.62rem;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-deep);
  border: 1px solid rgba(26, 107, 92, 0.18);
}

.status .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
}

.status.tone {
  background: rgba(21, 32, 40, 0.06);
  color: var(--ink-soft);
  border-color: rgba(21, 32, 40, 0.1);
}

.status.tone .dot {
  background: var(--muted);
}

.status.pending {
  background: var(--warn-soft);
  color: var(--warn);
  border-color: rgba(154, 91, 26, 0.2);
}

.status.pending .dot {
  background: var(--warn);
  animation: pulse-soft 1.4s ease-in-out infinite;
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

.composer {
  display: flex;
  gap: 0.55rem;
  align-items: center;
  padding-top: 0.85rem;
  border-top: 1px solid var(--line);
}

.composer-input {
  flex: 1;
  border-radius: 12px;
  padding: 0.7rem 1rem;
}

.composer-input:focus {
  background: #fff;
}

.pending-image {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.65rem;
  padding: 0.45rem 0.55rem;
  border: 1px solid rgba(26, 107, 92, 0.2);
  border-radius: 12px;
  background: var(--accent-soft);
  animation: rise-in 0.3s var(--ease);
}

.pending-thumb {
  width: 44px;
  height: 56px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--line-strong);
  box-shadow: 0 2px 6px rgba(21, 32, 40, 0.15);
}

.pending-text {
  flex: 1;
  font-size: 0.8rem;
  color: var(--accent-deep);
}

.pending-remove {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: var(--muted);
  transition: background 0.15s var(--ease), color 0.15s var(--ease);
}

.pending-remove:hover {
  background: rgba(21, 32, 40, 0.08);
  color: var(--ink);
}

.icon-btn {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  border: 1px solid var(--line);
  color: var(--ink-soft);
  background: rgba(255, 255, 255, 0.7);
  transition: background 0.2s var(--ease), border-color 0.2s var(--ease),
    transform 0.2s var(--ease), box-shadow 0.2s var(--ease);
}

.icon-btn:hover:not(:disabled) {
  border-color: var(--line-strong);
  background: #fff;
  transform: translateY(-1px);
  box-shadow: var(--shadow-lift);
}

.icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.icon-btn.recording {
  border-color: var(--error);
  color: var(--error);
  background: var(--error-soft);
  animation: pulse-soft 1.2s ease-in-out infinite;
}

.voice-hint {
  margin-bottom: 0.55rem;
  font-size: 0.8rem;
  color: var(--muted);
}

.voice-hint.recording {
  color: var(--error);
}

.speaker-btn {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  color: var(--accent-deep);
  cursor: pointer;
  transition: border-color 0.2s var(--ease), background 0.2s var(--ease),
    transform 0.2s var(--ease), box-shadow 0.2s var(--ease);
}

.speaker-btn:hover {
  border-color: var(--line-strong);
  background: #fff;
  transform: translateY(-1px);
  box-shadow: var(--shadow-lift);
}

.speaker-btn.muted {
  color: var(--muted);
}

.send {
  min-width: 5.6rem;
  border-radius: 12px;
}

.send-icon {
  margin-left: -0.1rem;
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
