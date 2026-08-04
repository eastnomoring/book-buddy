<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { listBooks, uploadBook } from '../api/client'
import { type BookInfo } from '@book-buddy/core'

const books = ref<BookInfo[]>([])
const selectedBook = ref<string | null>(null)
const loading = ref(false)
const uploading = ref(false)
const error = ref<string | null>(null)
const open = ref(false)
const rootEl = ref<HTMLElement | null>(null)

const emit = defineEmits<{
  select: [bookId: string]
}>()

async function loadBooks() {
  loading.value = true
  error.value = null
  try {
    books.value = await listBooks()
  } catch (e) {
    error.value = '加载书籍列表失败'
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function handleUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploading.value = true
  error.value = null

  try {
    await uploadBook(file, file.name.replace(/\.pdf$/i, ''))
    await loadBooks()
    input.value = ''
    open.value = true
    const timer = window.setInterval(async () => {
      await loadBooks()
      const stillParsing = books.value.some((b) => b.totalPages === 0)
      if (!stillParsing) {
        window.clearInterval(timer)
      }
    }, 1500)
    window.setTimeout(() => window.clearInterval(timer), 30000)
  } catch (e) {
    error.value = '上传失败'
    console.error(e)
  } finally {
    uploading.value = false
  }
}

function selectBook(bookId: string) {
  selectedBook.value = bookId
  emit('select', bookId)
  open.value = false
}

function selectedTitle() {
  const book = books.value.find((b) => b.id === selectedBook.value)
  return book?.title || '选择书籍'
}

function onDocClick(e: MouseEvent) {
  if (!rootEl.value) return
  if (!rootEl.value.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => {
  loadBooks()
  document.addEventListener('click', onDocClick)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
})
</script>

<template>
  <div class="book-bar" ref="rootEl">
    <button class="picker" type="button" @click="open = !open" :aria-expanded="open">
      <span class="picker-text">
        <span class="picker-kicker">当前书籍</span>
        <span class="picker-title">{{ selectedTitle() }}</span>
      </span>
      <svg class="picker-chevron" :class="{ flipped: open }" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>

    <label class="upload" :class="{ disabled: uploading }">
      {{ uploading ? '上传中' : '上传 PDF' }}
      <input
        type="file"
        accept=".pdf"
        @change="handleUpload"
        :disabled="uploading"
        hidden
      />
    </label>

    <div v-if="open" class="panel">
      <div v-if="loading" class="panel-state">加载中…</div>
      <div v-else-if="error" class="panel-state error">
        {{ error }}
        <button type="button" class="retry" @click="loadBooks">重试</button>
      </div>
      <div v-else-if="books.length === 0" class="panel-state">
        还没有书。上传一本 PDF 开始。
      </div>
      <ul v-else class="list">
        <li v-for="book in books" :key="book.id">
          <button
            type="button"
            class="item"
            :class="{ active: selectedBook === book.id }"
            @click="selectBook(book.id)"
          >
            <svg class="item-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M12 6.2C10.4 4.9 8.2 4.3 5.5 4.3c-.6 0-1.2.05-1.8.15v12.6c.6-.1 1.2-.15 1.8-.15 2.7 0 4.9.6 6.5 1.9 1.6-1.3 3.8-1.9 6.5-1.9.6 0 1.2.05 1.8.15V4.45c-.6-.1-1.2-.15-1.8-.15-2.7 0-4.9.6-6.5 1.9Z"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linejoin="round"
              />
              <path d="M12 6.2v12.6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
            </svg>
            <span class="item-title">{{ book.title }}</span>
            <span class="item-meta">
              <template v-if="book.totalPages < 0">解析失败</template>
              <template v-else-if="book.totalPages === 0">解析中</template>
              <template v-else>{{ book.totalPages }} 页</template>
            </span>
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.book-bar {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: min(420px, 100%);
}

.picker {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  text-align: left;
  padding: 0.55rem 0.85rem;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.7);
  transition: border-color 0.2s var(--ease), background 0.2s var(--ease),
    box-shadow 0.2s var(--ease), transform 0.2s var(--ease);
}

.picker:hover {
  border-color: var(--line-strong);
  background: #fff;
  transform: translateY(-1px);
  box-shadow: var(--shadow-lift);
}

.picker-text {
  min-width: 0;
}

.picker-kicker {
  display: block;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}

.picker-title {
  display: block;
  margin-top: 0.1rem;
  font-size: 0.95rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.picker-chevron {
  flex-shrink: 0;
  color: var(--muted);
  transition: transform 0.25s var(--ease);
}

.picker-chevron.flipped {
  transform: rotate(180deg);
}

.upload {
  flex-shrink: 0;
  padding: 0.75rem 0.95rem;
  border-radius: 12px;
  background: var(--accent-gradient);
  color: #f7fffc;
  font-size: 0.88rem;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(26, 107, 92, 0.25);
  transition: filter 0.2s var(--ease), box-shadow 0.2s var(--ease), transform 0.2s var(--ease);
}

.upload:hover:not(.disabled) {
  filter: brightness(1.06);
  transform: translateY(-1px);
  box-shadow: var(--shadow-accent);
}

.upload.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.panel {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  right: 0;
  z-index: 20;
  max-height: 300px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(14px);
  box-shadow: var(--shadow-pop);
  animation: rise-in 0.25s var(--ease);
}

.panel-state {
  padding: 1.1rem 1.15rem;
  color: var(--muted);
  font-size: 0.9rem;
}

.panel-state.error {
  color: var(--error);
}

.retry {
  display: inline-block;
  margin-top: 0.45rem;
  color: var(--accent-deep);
  text-decoration: underline;
}

.list {
  list-style: none;
  padding: 0.4rem;
}

.list li + li {
  border-top: 1px solid var(--line);
}

.item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.7rem 0.75rem;
  border-radius: 10px;
  text-align: left;
  transition: background 0.15s var(--ease);
}

.item:hover {
  background: var(--accent-soft);
}

.item.active {
  background: var(--accent-soft);
  box-shadow: inset 2px 0 0 var(--accent);
}

.item-icon {
  flex-shrink: 0;
  color: var(--accent);
  opacity: 0.85;
}

.item-title {
  flex: 1;
  min-width: 0;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-meta {
  flex-shrink: 0;
  font-size: 0.75rem;
  color: var(--muted);
  background: rgba(21, 32, 40, 0.05);
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}
</style>
