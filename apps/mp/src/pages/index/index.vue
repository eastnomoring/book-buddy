<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { MpChatTransport, type ToolEvent } from '../../platform/chatTransport'
import { listBooks, uploadBook } from '../../platform/books'
import { getApiBase, getConfig } from '../../platform/config'
import { readFileBase64, writeToolImage } from '../../platform/fs'
import { MpAudioRecorder } from '../../platform/audioRecorder'
import { MpTTSPlayer } from '../../platform/ttsPlayer'
import { transcribeVoice } from '../../platform/voice'
import { contentToNodes } from '../../utils/formula'
import CameraCapture from '../../components/CameraCapture.vue'
import type {
  ChatMessage,
  BookInfo,
  PhotoResult,
  ChatStreamHandle,
} from '@book-buddy/core'

/** 展示层消息：附加工具事件与落盘后的图片路径 */
interface UiMessage extends ChatMessage {
  toolEvents?: ToolEvent[]
  /** tool_result.images 落盘后的本地路径，按 tool id 索引 */
  toolImagePaths?: Record<string, string[]>
}

const chatTransport = new MpChatTransport()
const recorder = new MpAudioRecorder()
const ttsPlayer = ref(new MpTTSPlayer(false))
let currentHandle: ChatStreamHandle | null = null

const messages = ref<UiMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const error = ref('')
const books = ref<BookInfo[]>([])
const currentBookId = ref<string | null>(null)
const showCamera = ref(false)
const pendingImage = ref<PhotoResult | null>(null)
const isRecording = ref(false)
const isTranscribing = ref(false)
const voiceConfigured = ref(false)
const speakerOn = ref(true)

const currentBookTitle = computed(() => {
  const book = books.value.find((b) => b.id === currentBookId.value)
  return book?.title || '选择书籍'
})

const pickerIndex = computed(() => {
  const idx = books.value.findIndex((b) => b.id === currentBookId.value)
  return idx < 0 ? 0 : idx
})

const lastMessageId = computed(() => {
  if (loading.value) return 'msg-loading'
  const len = messages.value.length
  return len ? `msg-${len - 1}` : ''
})

onMounted(() => {
  loadBooks()
  loadConfig()
})

onUnmounted(() => {
  currentHandle?.abort()
  ttsPlayer.value.stop()
})

async function loadBooks() {
  try {
    books.value = await listBooks()
    if (books.value.length && !currentBookId.value) {
      currentBookId.value = books.value[0].id
    }
  } catch (e) {
    console.error('加载书籍列表失败', e)
    error.value = `加载书籍列表失败：${e instanceof Error ? e.message : String(e)}（${getApiBase()}）`
  }
}

async function loadConfig() {
  try {
    const cfg = await getConfig()
    voiceConfigured.value = cfg.voiceConfigured
    ttsPlayer.value = new MpTTSPlayer(speakerOn.value && cfg.voiceConfigured)
  } catch (e) {
    console.error('加载配置失败', e)
    error.value = `加载配置失败：${e instanceof Error ? e.message : String(e)}`
  }
}

function onBookChange(e: UniPickerChangeEvent) {
  const index = e.detail.value as number
  const book = books.value[index]
  if (book) currentBookId.value = book.id
}

function openSettings() {
  uni.navigateTo({ url: '/pages/settings/settings' })
}

function toggleSpeaker() {
  speakerOn.value = !speakerOn.value
  ttsPlayer.value.stop()
  ttsPlayer.value = new MpTTSPlayer(speakerOn.value && voiceConfigured.value)
}

function toggleCamera() {
  showCamera.value = !showCamera.value
}

function onCapture(result: PhotoResult) {
  pendingImage.value = result
  showCamera.value = false
}

function chooseFromAlbum() {
  uni.chooseImage({
    count: 1,
    sourceType: ['album'],
    success: async (res) => {
      const path = res.tempFilePaths[0]
      try {
        const base64 = await readFileBase64(path)
        const lower = path.toLowerCase()
        const mediaType = lower.endsWith('.png')
          ? 'image/png'
          : lower.endsWith('.gif')
            ? 'image/gif'
            : lower.endsWith('.webp')
              ? 'image/webp'
              : 'image/jpeg'
        pendingImage.value = { base64, mediaType }
      } catch (e) {
        error.value = e instanceof Error ? e.message : '读取图片失败'
      }
    },
    fail: (err) => {
      error.value = err.errMsg || '选择图片失败'
    },
  })
}

function removePendingImage() {
  pendingImage.value = null
}

async function toggleRecord() {
  if (isRecording.value) {
    isRecording.value = false
    isTranscribing.value = true
    try {
      const result = await recorder.stop()
      const transcription = await transcribeVoice(
        result.base64,
        result.mimeType.split('/')[1],
      )
      const text = transcription.text.trim()
      if (text) {
        inputText.value = text
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '语音识别失败'
    } finally {
      isTranscribing.value = false
    }
  } else {
    error.value = ''
    try {
      await recorder.start()
      isRecording.value = true
    } catch (e) {
      error.value = e instanceof Error ? e.message : '无法启动录音'
    }
  }
}

function chooseBookFile() {
  wx.chooseMessageFile({
    type: 'file',
    extension: ['pdf'],
    success: async (res) => {
      const file = res.tempFiles[0]
      if (!file) return
      uni.showLoading({ title: '上传中' })
      try {
        const title = file.name.replace(/\.pdf$/i, '')
        await uploadBook(file.path, title)
        await loadBooks()
        uni.showToast({ title: '上传成功', icon: 'success' })
      } catch (e) {
        error.value = e instanceof Error ? e.message : '上传失败'
      } finally {
        uni.hideLoading()
      }
    },
    fail: (err) => {
      if (err.errMsg?.includes('cancel')) return
      error.value = err.errMsg || '选择文件失败'
    },
  } as any)
}

function sendMessage() {
  const text = inputText.value.trim()
  if (!text && !pendingImage.value) return
  if (loading.value) return

  loading.value = true
  error.value = ''
  currentHandle?.abort()
  ttsPlayer.value.stop()

  const userMessage: ChatMessage = {
    role: 'user',
    content: text || '[图片]',
  }
  messages.value.push(userMessage)
  inputText.value = ''

  const history = messages.value.slice(0, -1).map((m) => ({
    role: m.role,
    content: m.content,
  }))

  messages.value.push({
    role: 'assistant',
    content: '',
    toolEvents: [],
    toolImagePaths: {},
  })
  const assistantIndex = messages.value.length - 1
  const assistantOf = () => messages.value[assistantIndex]

  const imageBase64 = pendingImage.value?.base64
  pendingImage.value = null

  // Z4：有服务端语音时走 chat 流内 type=audio；否则回退前端按句 /voice/synthesize
  const useServerStreamTts = speakerOn.value && voiceConfigured.value
  // 新一轮需可推送：stop() 会置 stopped，重建实例
  ttsPlayer.value = new MpTTSPlayer(speakerOn.value && voiceConfigured.value)

  currentHandle = chatTransport.chatStream(
    {
      text: text || undefined,
      image: imageBase64,
      bookId: currentBookId.value || undefined,
      history,
      enableTts: useServerStreamTts,
    },
    {
      onChunk: (delta) => {
        assistantOf().content += delta
        if (!useServerStreamTts) {
          ttsPlayer.value.push(delta)
        }
      },
      onAudioEvent: (ev) => {
        ttsPlayer.value.enqueueAudio(ev.base64, ev.mimeType)
      },
      onToolEvent: (ev) => {
        const msg = assistantOf()
        const prev = msg.toolEvents ?? []
        if (ev.type === 'tool_call') {
          msg.toolEvents = [...prev, ev]
        } else {
          const idx = prev.findIndex((e) => e.id === ev.id)
          if (idx >= 0) {
            const next = prev.slice()
            next[idx] = ev
            msg.toolEvents = next
          } else {
            msg.toolEvents = [...prev, ev]
          }
          // Z1：有图则落盘供 <image> 展示
          if (ev.images?.length) {
            void persistToolImages(assistantIndex, ev.id, ev.images)
          }
        }
      },
      onDone: () => {
        loading.value = false
        currentHandle = null
        if (!useServerStreamTts) {
          ttsPlayer.value.flush()
        }
      },
      onError: (err) => {
        error.value = err.message || '发送失败，请重试'
        messages.value = messages.value.slice(0, -1)
        loading.value = false
        currentHandle = null
        ttsPlayer.value.stop()
      },
    },
  )
}

async function persistToolImages(
  messageIndex: number,
  toolId: string,
  images: { base64: string; mediaType: string }[],
) {
  try {
    const paths: string[] = []
    for (let i = 0; i < images.length; i++) {
      const img = images[i]
      const path = await writeToolImage(img.base64, img.mediaType, `${toolId}_${i}`)
      paths.push(path)
    }
    const msg = messages.value[messageIndex]
    if (!msg) return
    msg.toolImagePaths = {
      ...(msg.toolImagePaths || {}),
      [toolId]: paths,
    }
  } catch (e) {
    console.error('工具图片落盘失败', e)
  }
}

function playLastAnswer() {
  const last = messages.value
    .slice()
    .reverse()
    .find((m) => m.role === 'assistant')
  if (last) ttsPlayer.value.playText(last.content)
}
</script>

<template>
  <view class="page">
    <view class="top-bar">
      <picker
        v-if="books.length"
        mode="selector"
        :range="books"
        range-key="title"
        :value="pickerIndex"
        @change="onBookChange"
      >
        <view class="book-picker">
          <text class="book-label">当前书籍</text>
          <text class="book-title">{{ currentBookTitle }}</text>
        </view>
      </picker>
      <view v-else class="book-picker">
        <text class="book-label">当前书籍</text>
        <text class="book-title">未加载</text>
      </view>

      <view class="top-actions">
        <view class="icon-btn upload" @click="chooseBookFile">上传</view>
        <view
          class="icon-btn speaker"
          :class="{ muted: !speakerOn || !voiceConfigured }"
          @click="toggleSpeaker"
        >
          {{ speakerOn && voiceConfigured ? '朗读开' : '朗读关' }}
        </view>
        <view class="icon-btn settings" @click="openSettings">设置</view>
      </view>
    </view>

    <scroll-view
      class="messages"
      scroll-y
      :scroll-into-view="lastMessageId"
      scroll-with-animation
    >
      <view v-if="messages.length === 0" class="empty">
        <text class="empty-title">从一页书开始</text>
        <text class="empty-copy">拍照、选图、录音或输入问题。</text>
      </view>

      <view
        v-for="(msg, idx) in messages"
        :id="`msg-${idx}`"
        :key="idx"
        class="bubble"
        :class="msg.role"
      >
        <view class="bubble-inner">
          <view class="bubble-header">
            <text class="bubble-label">{{ msg.role === 'user' ? '你' : '伴读' }}</text>
            <text
              v-if="msg.role === 'assistant' && voiceConfigured"
              class="play-btn"
              @click="playLastAnswer"
            >
              朗读
            </text>
          </view>
          <view v-if="msg.toolEvents?.length" class="tool-events">
            <view
              v-for="ev in msg.toolEvents"
              :key="ev.id"
              class="tool-event"
              :class="{
                running: ev.type === 'tool_call',
                failed: ev.type === 'tool_result' && !ev.ok,
              }"
            >
              <view class="tool-head">
                <text class="tool-name">{{ ev.name }}</text>
                <text class="tool-status">
                  {{ ev.type === 'tool_call' ? '运行中…' : ev.ok ? '完成' : '失败' }}
                </text>
              </view>
              <text
                v-if="ev.type === 'tool_result' && ev.preview"
                class="tool-preview"
              >{{ ev.preview }}</text>
              <view
                v-if="msg.toolImagePaths?.[ev.id]?.length"
                class="tool-images"
              >
                <image
                  v-for="(src, imgIdx) in msg.toolImagePaths[ev.id]"
                  :key="`${ev.id}-${imgIdx}`"
                  class="tool-image"
                  :src="src"
                  mode="widthFix"
                />
              </view>
            </view>
          </view>
          <!-- P4：公式经后端 /render/formula 渲染为图片，其余文本原样展示 -->
          <rich-text
            class="bubble-body"
            :nodes="msg.role === 'assistant' ? contentToNodes(msg.content) : [{ type: 'text', text: msg.content }]"
          />
        </view>
      </view>

      <view v-if="loading" id="msg-loading" class="bubble assistant">
        <view class="bubble-inner">
          <text class="bubble-label">伴读</text>
          <view class="typing">
            <text></text>
            <text></text>
            <text></text>
          </view>
        </view>
      </view>

      <view v-if="error" class="error-banner">{{ error }}</view>
    </scroll-view>

    <view v-if="pendingImage" class="pending-image">
      <image
        class="pending-thumb"
        :src="'data:' + pendingImage.mediaType + ';base64,' + pendingImage.base64"
        mode="aspectFill"
      />
      <text class="pending-text">将随下一条消息发送</text>
      <text class="pending-remove" @click="removePendingImage">移除</text>
    </view>

    <view class="composer">
      <view class="icon-btn camera" @click="toggleCamera">拍照</view>
      <view class="icon-btn album" @click="chooseFromAlbum">相册</view>
      <view
        class="icon-btn record"
        :class="{ recording: isRecording }"
        @click="toggleRecord"
      >
        {{ isRecording ? '结束' : isTranscribing ? '识别' : '录音' }}
      </view>
      <input
        v-model="inputText"
        class="composer-input"
        placeholder="这一页哪里卡住了？"
        confirm-type="send"
        @confirm="sendMessage"
      />
      <button
        class="send-btn"
        :disabled="loading || (!inputText.trim() && !pendingImage)"
        @click="sendMessage"
      >
        发送
      </button>
    </view>

    <CameraCapture
      v-if="showCamera"
      @capture="onCapture"
      @close="toggleCamera"
    />
  </view>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(165deg, #f4f7f8 0%, #eef2f4 42%, #e2e8ec 100%);
  color: #152028;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid rgba(21, 32, 40, 0.1);
  background: rgba(255, 255, 255, 0.72);
}

.book-picker {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.book-label {
  font-size: 0.58rem;
  color: #6b7884;
  letter-spacing: 0.04em;
}

.book-title {
  font-size: 0.85rem;
  font-weight: 500;
  color: #152028;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-actions {
  display: flex;
  gap: 0.35rem;
  flex-shrink: 0;
}

.icon-btn {
  font-size: 0.7rem;
  color: #1a6b5c;
  padding: 0.3rem 0.55rem;
  border: 1px solid rgba(26, 107, 92, 0.25);
  border-radius: 8px;
  background: rgba(26, 107, 92, 0.08);
  white-space: nowrap;
}

.icon-btn.muted {
  color: #6b7884;
  border-color: rgba(21, 32, 40, 0.15);
  background: rgba(21, 32, 40, 0.05);
}

.icon-btn.recording {
  color: #b42318;
  border-color: rgba(180, 35, 24, 0.3);
  background: rgba(180, 35, 24, 0.1);
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 0.6rem 0.8rem;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-top: 30vh;
  text-align: center;
}

.empty-title {
  font-size: 1.15rem;
  font-weight: 500;
  color: #1a6b5c;
  margin-bottom: 0.3rem;
}

.empty-copy {
  font-size: 0.78rem;
  color: #6b7884;
}

.bubble {
  display: flex;
  margin-bottom: 0.75rem;
}

.bubble.user {
  justify-content: flex-end;
}

.bubble-inner {
  max-width: 85%;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.bubble-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin: 0 0.25rem;
}

.bubble-label {
  font-size: 0.58rem;
  color: #6b7884;
}

.play-btn {
  font-size: 0.58rem;
  color: #1a6b5c;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  background: rgba(26, 107, 92, 0.1);
}

.bubble-body {
  padding: 0.6rem 0.8rem;
  border-radius: 12px;
  line-height: 1.55;
  font-size: 0.9rem;
  word-break: break-word;
}

.bubble.user .bubble-body {
  background: #152028;
  color: #f4f7f8;
  border-bottom-right-radius: 4px;
}

.bubble.assistant .bubble-body {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(21, 32, 40, 0.1);
  border-bottom-left-radius: 4px;
}

.tool-events {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin-bottom: 0.25rem;
}

.tool-event {
  padding: 0.4rem 0.55rem;
  border: 1px solid rgba(26, 107, 92, 0.2);
  border-radius: 10px;
  background: rgba(26, 107, 92, 0.06);
}

.tool-event.failed {
  border-color: rgba(180, 35, 24, 0.3);
  background: rgba(180, 35, 24, 0.06);
}

.tool-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
}

.tool-name {
  font-size: 0.72rem;
  font-weight: 500;
  color: #1a6b5c;
}

.tool-event.failed .tool-name {
  color: #b42318;
}

.tool-status {
  font-size: 0.65rem;
  color: #6b7884;
}

.tool-preview {
  display: block;
  margin-top: 0.3rem;
  padding: 0.35rem 0.4rem;
  border-radius: 6px;
  background: rgba(21, 32, 40, 0.05);
  font-size: 0.65rem;
  line-height: 1.45;
  color: #3d4a55;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 8rem;
  overflow-y: auto;
}

.tool-images {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-top: 0.35rem;
}

.tool-image {
  width: 100%;
  border-radius: 8px;
  border: 1px solid rgba(21, 32, 40, 0.1);
  background: #fff;
}

.typing {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0.7rem 0.8rem;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(21, 32, 40, 0.1);
  border-radius: 12px;
  border-bottom-left-radius: 4px;
}

.typing text {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #1a6b5c;
  animation: typing-dot 1.2s ease-in-out infinite;
}

.typing text:nth-child(2) {
  animation-delay: 0.15s;
}

.typing text:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes typing-dot {
  0%,
  100% {
    opacity: 0.35;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

.error-banner {
  margin: 0.5rem 0;
  padding: 0.5rem 0.7rem;
  border-radius: 8px;
  background: rgba(180, 35, 24, 0.1);
  color: #b42318;
  font-size: 0.78rem;
}

.pending-image {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0.8rem 0.5rem;
  padding: 0.4rem 0.55rem;
  border: 1px solid rgba(26, 107, 92, 0.2);
  border-radius: 10px;
  background: rgba(26, 107, 92, 0.06);
}

.pending-thumb {
  width: 40px;
  height: 52px;
  border-radius: 6px;
  background: #fff;
}

.pending-text {
  flex: 1;
  font-size: 0.75rem;
  color: #145447;
}

.pending-remove {
  font-size: 0.72rem;
  color: #b42318;
  padding: 0.15rem 0.4rem;
}

.composer {
  display: flex;
  gap: 0.35rem;
  align-items: center;
  padding: 0.55rem 0.7rem calc(0.55rem + env(safe-area-inset-bottom));
  border-top: 1px solid rgba(21, 32, 40, 0.1);
  background: rgba(255, 255, 255, 0.85);
}

.composer-input {
  flex: 1;
  min-width: 0;
  padding: 0.5rem 0.65rem;
  border: 1px solid rgba(21, 32, 40, 0.12);
  border-radius: 10px;
  background: #fff;
  font-size: 0.85rem;
}

.send-btn {
  flex-shrink: 0;
  padding: 0.5rem 0.85rem;
  border-radius: 10px;
  font-size: 0.85rem;
  font-weight: 500;
  color: #f7fffc;
  background: linear-gradient(135deg, #22907b 0%, #1a6b5c 55%, #145447 100%);
  box-shadow: 0 2px 6px rgba(26, 107, 92, 0.25);
}

.send-btn[disabled] {
  opacity: 0.45;
}
</style>
