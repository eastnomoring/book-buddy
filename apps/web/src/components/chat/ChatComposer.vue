<script setup lang="ts">
defineProps<{
  modelValue: string
  isLoading: boolean
  isRecording: boolean
  isTranscribing: boolean
  image?: string | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  send: []
  toggleVoice: []
  clearImage: []
}>()

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}
</script>

<template>
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
      @click="emit('toggleVoice')"
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
      :value="modelValue"
      @input="onInput"
      @keyup.enter="emit('send')"
      :disabled="isLoading"
      placeholder="这一页哪里卡住了？"
      class="composer-input"
    />

    <button
      @click="emit('send')"
      class="btn btn-primary send"
      :disabled="isLoading || (!modelValue.trim() && !image)"
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
</template>

<style scoped>
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

.send {
  min-width: 5.6rem;
  border-radius: 12px;
}

.send-icon {
  margin-left: -0.1rem;
}
</style>
