<script setup lang="ts">
import { computed } from 'vue'
import type { PhotoResult } from '@book-buddy/core'

const props = defineProps<{
  modelValue: string
  loading: boolean
  pendingImage: PhotoResult | null
  isRecording: boolean
  isTranscribing: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  send: []
  camera: []
  album: []
  record: []
}>()

const text = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value),
})
</script>

<template>
  <view class="composer">
    <view class="icon-btn camera" @click="emit('camera')">拍照</view>
    <view class="icon-btn album" @click="emit('album')">相册</view>
    <view
      class="icon-btn record"
      :class="{ recording: isRecording }"
      @click="emit('record')"
    >
      {{ isRecording ? '结束' : isTranscribing ? '识别' : '录音' }}
    </view>
    <input
      v-model="text"
      class="composer-input"
      placeholder="这一页哪里卡住了？"
      confirm-type="send"
      @confirm="emit('send')"
    />
    <button
      class="send-btn"
      :disabled="loading || (!modelValue.trim() && !pendingImage)"
      @click="emit('send')"
    >
      发送
    </button>
  </view>
</template>

<style scoped>
.composer {
  display: flex;
  gap: 0.35rem;
  align-items: center;
  padding: 0.55rem 0.7rem calc(0.55rem + env(safe-area-inset-bottom));
  border-top: 1px solid rgba(21, 32, 40, 0.1);
  background: rgba(255, 255, 255, 0.85);
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

.icon-btn.recording {
  color: #b42318;
  border-color: rgba(180, 35, 24, 0.3);
  background: rgba(180, 35, 24, 0.1);
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
