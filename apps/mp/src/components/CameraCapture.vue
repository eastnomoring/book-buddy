<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { readFileBase64 } from '../platform/fs'
import { PlatformError, type PhotoResult } from '@book-buddy/core'

const emit = defineEmits<{
  capture: [result: PhotoResult]
  close: []
}>()

const cameraContext = ref<UniApp.CameraContext>()
const error = ref('')

onMounted(() => {
  cameraContext.value = uni.createCameraContext()
})

onUnmounted(() => {
  // camera 组件无显式销毁 API
})

function inferMediaType(path: string): string {
  const lower = path.toLowerCase()
  if (lower.endsWith('.png')) return 'image/png'
  if (lower.endsWith('.gif')) return 'image/gif'
  if (lower.endsWith('.webp')) return 'image/webp'
  return 'image/jpeg'
}

async function takePhoto() {
  if (!cameraContext.value) return
  try {
    const res = await new Promise<UniApp.CameraContextTakePhotoResult>(
      (resolve, reject) => {
        cameraContext.value!.takePhoto({
          quality: 'normal',
          success: resolve,
          fail: (err) =>
            reject(new PlatformError(err.errMsg || 'takePhoto failed', err)),
        })
      },
    )
    const base64 = await readFileBase64(res.tempImagePath)
    emit('capture', {
      base64,
      mediaType: inferMediaType(res.tempImagePath),
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '拍照失败'
  }
}

function chooseFromAlbum() {
  uni.chooseImage({
    count: 1,
    sourceType: ['album'],
    success: async (res) => {
      const path = res.tempFilePaths[0]
      try {
        const base64 = await readFileBase64(path)
        emit('capture', {
          base64,
          mediaType: inferMediaType(path),
        })
      } catch (e) {
        error.value = e instanceof Error ? e.message : '读取图片失败'
      }
    },
    fail: (err) => {
      error.value = err.errMsg || '选择图片失败'
    },
  })
}

function close() {
  emit('close')
}
</script>

<template>
  <view class="camera-panel">
    <camera class="camera" mode="normal" resolution="medium" flash="auto" />
    <view v-if="error" class="camera-error">{{ error }}</view>
    <view class="camera-controls">
      <view class="control-btn album" @click="chooseFromAlbum">相册</view>
      <view class="shutter" @click="takePhoto" />
      <view class="control-btn close" @click="close">关闭</view>
    </view>
  </view>
</template>

<style scoped>
.camera-panel {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  flex-direction: column;
  background: #000;
}

.camera {
  flex: 1;
  width: 100%;
}

.camera-error {
  position: absolute;
  top: 1rem;
  left: 1rem;
  right: 1rem;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  background: rgba(180, 35, 24, 0.9);
  color: #fff;
  font-size: 0.82rem;
  text-align: center;
}

.camera-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 2rem calc(1.25rem + env(safe-area-inset-bottom));
  background: rgba(0, 0, 0, 0.35);
}

.control-btn {
  color: #fff;
  font-size: 0.85rem;
  padding: 0.5rem 0.9rem;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.18);
}

.shutter {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #fff;
  border: 4px solid rgba(255, 255, 255, 0.35);
}
</style>
