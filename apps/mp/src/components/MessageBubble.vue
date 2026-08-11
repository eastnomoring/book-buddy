<script setup lang="ts">
import { contentToNodes } from '../utils/formula'
import ToolEventList from './ToolEventList.vue'
import type { UiMessage } from '../types'

defineProps<{
  msg: UiMessage
  voiceConfigured: boolean
}>()

defineEmits<{
  play: []
}>()
</script>

<template>
  <view class="bubble" :class="msg.role">
    <view class="bubble-inner">
      <view class="bubble-header">
        <text class="bubble-label">{{ msg.role === 'user' ? '你' : '伴读' }}</text>
        <text
          v-if="msg.role === 'assistant' && voiceConfigured"
          class="play-btn"
          @click="$emit('play')"
        >
          朗读
        </text>
      </view>
      <ToolEventList
        v-if="msg.toolEvents?.length"
        :events="msg.toolEvents"
        :image-paths="msg.toolImagePaths"
      />
      <!-- P4：公式经后端 /render/formula 渲染为图片，其余文本原样展示 -->
      <rich-text
        class="bubble-body"
        :nodes="msg.role === 'assistant' ? contentToNodes(msg.content) : [{ type: 'text', text: msg.content }]"
      />
    </view>
  </view>
</template>

<style scoped>
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
</style>
