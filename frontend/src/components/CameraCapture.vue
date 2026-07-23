<script setup lang="ts">
import { ref, onUnmounted } from 'vue'

const props = defineProps<{
  currentPage?: number
}>()

const emit = defineEmits<{
  capture: [imageBase64: string]
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
        facingMode: 'environment', // 后置摄像头（适合拍书）
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
  
  // 转为 base64（去掉前缀）
  const dataUrl = canvas.toDataURL('image/jpeg', 0.8)
  const base64 = dataUrl.split(',')[1]
  
  capturedPreview.value = dataUrl
  emit('capture', base64)
  
  // 停止摄像头
  stopCamera()
}

function clearCapture() {
  capturedPreview.value = null
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
  <div class="camera-capture card">
    <div class="capture-header">
      <h3>📷 拍照</h3>
      <span v-if="pageInput" class="page-indicator">
        第 {{ pageInput }} 页
      </span>
    </div>

    <div class="page-input-area">
      <label>当前页码：</label>
      <input 
        type="number" 
        v-model.number="pageInput"
        @change="updatePage"
        min="1"
        class="page-input"
      />
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <div class="video-container">
      <video 
        v-show="isStreaming && !capturedPreview"
        ref="videoRef"
        autoplay
        playsinline
        muted
        class="video"
      ></video>

      <img 
        v-if="capturedPreview" 
        :src="capturedPreview" 
        class="preview-image"
        alt="捕获的图像"
      />

      <div v-if="!isStreaming && !capturedPreview" class="placeholder">
        <div class="placeholder-icon">📷</div>
        <p>点击下方按钮开启摄像头</p>
      </div>
    </div>

    <canvas ref="canvasRef" style="display: none;"></canvas>

    <div class="controls">
      <template v-if="!isStreaming && !capturedPreview">
        <button @click="startCamera" class="btn btn-primary">
          开启摄像头
        </button>
      </template>

      <template v-else-if="isStreaming && !capturedPreview">
        <button @click="capturePhoto" class="btn btn-primary">
          📸 拍照
        </button>
        <button @click="stopCamera" class="btn">
          取消
        </button>
      </template>

      <template v-else-if="capturedPreview">
        <button @click="clearCapture" class="btn">
          重新拍摄
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.camera-capture {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.capture-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.capture-header h3 {
  margin: 0;
  font-size: 1rem;
}

.page-indicator {
  font-size: 0.875rem;
  color: var(--primary);
  font-weight: 500;
}

.page-input-area {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.page-input {
  width: 80px;
  padding: 0.5rem;
}

.video-container {
  position: relative;
  aspect-ratio: 3/4;
  background: #1a1a1a;
  border-radius: 8px;
  overflow: hidden;
}

.video,
.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #666;
}

.placeholder-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
}

.controls {
  display: flex;
  gap: 0.75rem;
}

.error-message {
  padding: 0.75rem;
  background: #fee;
  color: var(--error);
  border-radius: 6px;
  font-size: 0.875rem;
}
</style>