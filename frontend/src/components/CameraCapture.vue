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
        <span class="idle-mark" aria-hidden="true">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
            <path
              d="M4 8.5A1.5 1.5 0 0 1 5.5 7h2L9 4.8A1 1 0 0 1 9.9 4.4h4.2a1 1 0 0 1 .9.4l1.5 2.2h2A1.5 1.5 0 0 1 20 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5v-9Z"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linejoin="round"
            />
            <circle cx="12" cy="12.8" r="3.2" stroke="currentColor" stroke-width="1.5" />
          </svg>
        </span>
        <p>开启摄像头拍摄纸质书页</p>
      </div>

      <div v-if="isStreaming && !capturedPreview" class="live-tag">
        <i class="live-dot" aria-hidden="true"></i>取景中
      </div>
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
  border-radius: 10px;
}

.viewport {
  position: relative;
  flex: 1;
  min-height: 320px;
  aspect-ratio: 3 / 4;
  border-radius: calc(var(--radius) - 2px);
  overflow: hidden;
  border: 1px solid var(--line);
  box-shadow: var(--shadow-lift), inset 0 0 0 1px rgba(255, 255, 255, 0.06);
  background:
    radial-gradient(420px 300px at 50% 0%, rgba(26, 107, 92, 0.18), transparent 60%),
    linear-gradient(160deg, #1c2430 0%, #2a3540 100%);
}

.viewport.live {
  border-color: rgba(26, 107, 92, 0.55);
  box-shadow: var(--shadow-lift), 0 0 0 3px var(--accent-soft);
}

.viewport.snapped {
  border-color: rgba(26, 107, 92, 0.4);
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
  gap: 0.95rem;
  color: rgba(247, 249, 250, 0.72);
  font-size: 0.9rem;
  text-align: center;
  padding: 1.5rem;
}

.idle-mark {
  display: grid;
  place-items: center;
  width: 60px;
  height: 60px;
  border: 1px solid rgba(247, 249, 250, 0.22);
  border-radius: 18px;
  color: rgba(247, 249, 250, 0.75);
  background: rgba(255, 255, 255, 0.05);
}

.live-tag {
  position: absolute;
  top: 0.75rem;
  left: 0.75rem;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.65rem;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #e8fff8;
  background: rgba(20, 84, 71, 0.85);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(232, 255, 248, 0.22);
  border-radius: 999px;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #7be0c4;
  animation: pulse-soft 1.6s ease-in-out infinite;
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
