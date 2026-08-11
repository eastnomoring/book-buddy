<script setup lang="ts">
import { computed } from 'vue'
import MessageBubble from './MessageBubble.vue'
import type { UiMessage } from '../types'

const props = defineProps<{
  messages: UiMessage[]
  loading: boolean
  error: string
  voiceConfigured: boolean
}>()

defineEmits<{
  play: []
}>()

const lastMessageId = computed(() => {
  if (props.loading) return 'msg-loading'
  const len = props.messages.length
  return len ? `msg-${len - 1}` : ''
})
</script>

<template>
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

    <MessageBubble
      v-for="(msg, idx) in messages"
      :id="`msg-${idx}`"
      :key="idx"
      :msg="msg"
      :voice-configured="voiceConfigured"
      @play="$emit('play')"
    />

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
</template>

<style scoped>
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

.bubble-inner {
  max-width: 85%;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.bubble-label {
  font-size: 0.58rem;
  color: #6b7884;
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
</style>
