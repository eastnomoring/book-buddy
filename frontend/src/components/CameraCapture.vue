<script setup lang="ts">
import { ref, onUnmounted } from 'vue'

const props = defineProps<{
  currentPage?: number
}>()

const emit = defineEmits<{
  capture: [imageBase64: string]
  clear: []
  pageChange: [page: number]
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const capturedPreview = ref<string | null>(null)
const isStreaming = ref(false)
const error = ref<string | null>(null)
const pageInput = ref(props.currentPage || 1)

let stream: MediaStream | null = null

async function startCamera() {
  try {
    error.value = null
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: 'environment',
        width: { ideal: 1920 },
        height: { ideal: 1080 },
      },
      audio: false,
    })

    if (videoRef.value) {
      videoRef.value.srcObject = stream
      isStreaming.value = true
    }
  } catch (e) {
    error.value = '无法访问摄像头，请检查权限设置'
    console.error(e)
  }
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
    stream = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
  isStreaming.value = false
}

function capturePhoto() {
  if (!videoRef.value || !canvasRef.value) return

  const video = videoRef.value
  const canvas = canvasRef.value

  canvas.width = video.videoWidth
  canvas.height = video.videoHeight

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

  const dataUrl = canvas.toDataURL('image/jpeg', 0.8)
  const base64 = dataUrl.split(',')[1]

  capturedPreview.value = dataUrl
  emit('capture', base64)
  stopCamera()
}

function clearCapture() {
  capturedPreview.value = null
  emit('clear')
}

function updatePage() {
  const page = parseInt(pageInput.value.toString())
  if (page > 0) {
    emit('pageChange', page)
  }
}

onUnmounted(() => {
  stopCamera()
})
</script>

<template>
  <div class="capture">
    <div class="capture-top">
      <div>
        <h2 class="pane-title">书页</h2>
        <p class="pane-sub">对准当前页，拍下后即可提问</p>
      </div>
      <label class="page-field">
        <span>页码</span>
        <input
          type="number"
          v-model.number="pageInput"
          @change="updatePage"
          min="1"
        />
      </label>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <div class="viewport" :class="{ live: isStreaming, snapped: !!capturedPreview }">
      <video
        v-show="isStreaming && !capturedPreview"
        ref="videoRef"
        autoplay
        playsinline
        muted
        class="feed"
      ></video>

      <img
        v-if="capturedPreview"
        :src="capturedPreview"
        class="feed"
        alt="已拍摄书页"
      />

      <div v-if="!isStreaming && !capturedPreview" class="idle">
        <span class="idle-mark" aria-hidden="true"></span>
        <p>开启摄像头拍摄纸质书页</p>
      </div>

      <div v-if="isStreaming && !capturedPreview" class="live-tag">取景中</div>
    </div>

    <canvas ref="canvasRef" hidden></canvas>

    <div class="actions">
      <template v-if="!isStreaming && !capturedPreview">
        <button @click="startCamera" class="btn btn-primary">开启摄像头</button>
      </template>

      <template v-else-if="isStreaming && !capturedPreview">
        <button @click="capturePhoto" class="btn btn-primary">拍摄</button>
        <button @click="stopCamera" class="btn btn-ghost">取消</button>
      </template>

      <template v-else-if="capturedPreview">
        <button @click="clearCapture" class="btn btn-ghost">重新拍摄</button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.capture {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  height: 100%;
  padding: 1.15rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--surface);
  backdrop-filter: blur(10px);
  box-shadow: var(--shadow-soft);
}

.capture-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
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

.page-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
}

.page-field input {
  width: 4.5rem;
  padding: 0.45rem 0.55rem;
  text-align: center;
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--ink);
}

.viewport {
  position: relative;
  flex: 1;
  min-height: 320px;
  aspect-ratio: 3 / 4;
  border-radius: calc(var(--radius) - 4px);
  overflow: hidden;
  background:
    linear-gradient(160deg, #1c2430 0%, #2a3540 100%);
}

.viewport.live {
  outline: 1px solid rgba(26, 107, 92, 0.45);
  outline-offset: -1px;
}

.viewport.snapped {
  outline: 1px solid rgba(26, 107, 92, 0.35);
  outline-offset: -1px;
}

.feed {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  animation: fade-in 0.35s var(--ease);
}

.idle {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.85rem;
  color: rgba(247, 249, 250, 0.72);
  font-size: 0.9rem;
  text-align: center;
  padding: 1.5rem;
}

.idle-mark {
  width: 42px;
  height: 42px;
  border: 1.5px solid rgba(247, 249, 250, 0.35);
  border-radius: 50% 50% 40% 60%;
  position: relative;
}

.idle-mark::after {
  content: "";
  position: absolute;
  inset: 10px;
  border: 1.5px solid rgba(247, 249, 250, 0.55);
  border-radius: 40% 60% 50% 50%;
}

.live-tag {
  position: absolute;
  top: 0.75rem;
  left: 0.75rem;
  padding: 0.28rem 0.55rem;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #e8fff8;
  background: rgba(26, 107, 92, 0.85);
  border-radius: 4px;
  animation: pulse-soft 1.8s ease-in-out infinite;
}

.actions {
  display: flex;
  gap: 0.6rem;
}

.error-banner {
  padding: 0.65rem 0.8rem;
  border-radius: var(--radius-sm);
  background: var(--error-soft);
  color: var(--error);
  font-size: 0.86rem;
}
</style>
