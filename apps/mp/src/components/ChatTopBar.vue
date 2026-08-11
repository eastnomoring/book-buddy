<script setup lang="ts">
import { computed } from 'vue'
import type { BookInfo } from '@book-buddy/core'

/** uni picker change 事件（@dcloudio/types 未内置此类型） */
interface UniPickerChangeEvent {
  detail: { value: number }
}

const props = defineProps<{
  books: BookInfo[]
  bookId: string | null
  speakerOn: boolean
  voiceConfigured: boolean
}>()

const emit = defineEmits<{
  bookChange: [id: string]
  upload: []
  toggleSpeaker: []
  settings: []
}>()

const currentBookTitle = computed(() => {
  const book = props.books.find((b) => b.id === props.bookId)
  return book?.title || '选择书籍'
})

const pickerIndex = computed(() => {
  const idx = props.books.findIndex((b) => b.id === props.bookId)
  return idx < 0 ? 0 : idx
})

function onBookChange(e: UniPickerChangeEvent) {
  const index = e.detail.value
  const book = props.books[index]
  if (book) emit('bookChange', book.id)
}
</script>

<template>
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
      <view class="icon-btn upload" @click="emit('upload')">上传</view>
      <view
        class="icon-btn speaker"
        :class="{ muted: !speakerOn || !voiceConfigured }"
        @click="emit('toggleSpeaker')"
      >
        {{ speakerOn && voiceConfigured ? '朗读开' : '朗读关' }}
      </view>
      <view class="icon-btn settings" @click="emit('settings')">设置</view>
    </view>
  </view>
</template>

<style scoped>
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
</style>
