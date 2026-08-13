<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { MpChatTransport } from '../../platform/chatTransport'
import { listBooks, uploadBook } from '../../platform/books'
import { getApiBase, getConfig } from '../../platform/config'
import { readFileBase64, writeToolImage } from '../../platform/fs'
import { MpTTSPlayer } from '../../platform/ttsPlayer'
import { useVoiceInput } from './useVoiceInput'
import CameraCapture from '../../components/CameraCapture.vue'
import ChatTopBar from '../../components/ChatTopBar.vue'
import MessageList from '../../components/MessageList.vue'
import ChatComposer from '../../components/ChatComposer.vue'
import type { UiMessage } from '../../types'
import type {
  ChatMessage,
  BookInfo,
  PhotoResult,
  ChatStreamHandle,
} from '@book-buddy/core'

const chatTransport = new MpChatTransport()
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
const voiceConfigured = ref(false)
const speakerOn = ref(true)

const { isRecording, isTranscribing, toggleRecord } = useVoiceInput({ inputText, error })

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

function onBookChange(id: string) {
  currentBookId.value = id
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

function chooseBookFile() {
  wx.chooseMessageFile({
    count: 1,
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
  })
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
    <ChatTopBar
      :books="books"
      :book-id="currentBookId"
      :speaker-on="speakerOn"
      :voice-configured="voiceConfigured"
      @book-change="onBookChange"
      @upload="chooseBookFile"
      @toggle-speaker="toggleSpeaker"
      @settings="openSettings"
    />

    <MessageList
      class="message-list"
      :messages="messages"
      :loading="loading"
      :error="error"
      :voice-configured="voiceConfigured"
      @play="playLastAnswer"
    />

    <view v-if="pendingImage" class="pending-image">
      <image
        class="pending-thumb"
        :src="'data:' + pendingImage.mediaType + ';base64,' + pendingImage.base64"
        mode="aspectFill"
      />
      <text class="pending-text">将随下一条消息发送</text>
      <text class="pending-remove" @click="removePendingImage">移除</text>
    </view>

    <ChatComposer
      v-model="inputText"
      :loading="loading"
      :pending-image="pendingImage"
      :is-recording="isRecording"
      :is-transcribing="isTranscribing"
      @camera="toggleCamera"
      @album="chooseFromAlbum"
      @record="toggleRecord"
      @send="sendMessage"
    />

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

/* 小程序自定义组件宿主节点高度自适应内容，flex:1 写在 MessageList 内部不生效，
   需在父级把宿主节点撑开，输入栏才能被顶到底部 */
.message-list {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
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
</style>
