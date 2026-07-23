<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listBooks, uploadBook, type BookInfo } from '../api/client'

const books = ref<BookInfo[]>([])
const selectedBook = ref<string | null>(null)
const loading = ref(false)
const uploading = ref(false)
const error = ref<string | null>(null)

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
    await uploadBook(file, file.name.replace('.pdf', ''))
    await loadBooks()
    input.value = '' // 清空 input
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
}

onMounted(loadBooks)
</script>

<template>
  <div class="book-selector">
    <div class="selector-header">
      <label class="select-label">当前书籍</label>
      <div class="upload-area">
        <label class="upload-btn" :class="{ disabled: uploading }">
          {{ uploading ? '上传中...' : '上传新书' }}
          <input 
            type="file" 
            accept=".pdf" 
            @change="handleUpload"
            :disabled="uploading"
            hidden
          />
        </label>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      加载中...
    </div>

    <div v-else-if="error" class="error-state">
      {{ error }}
      <button @click="loadBooks" class="retry-btn">重试</button>
    </div>

    <div v-else-if="books.length === 0" class="empty-state">
      <p>暂无书籍</p>
      <p class="hint">上传一本 PDF 开始学习吧</p>
    </div>

    <div v-else class="book-list">
      <button
        v-for="book in books"
        :key="book.id"
        class="book-item"
        :class="{ active: selectedBook === book.id }"
        @click="selectBook(book.id)"
      >
        <span class="book-title">{{ book.title }}</span>
        <span class="book-pages">{{ book.totalPages }} 页</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.book-selector {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.selector-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.select-label {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.upload-btn {
  padding: 0.5rem 1rem;
  background: var(--primary);
  color: white;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.2s;
}

.upload-btn:hover:not(.disabled) {
  background: var(--primary-light);
}

.upload-btn.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.book-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.book-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.book-item:hover {
  border-color: var(--primary);
}

.book-item.active {
  border-color: var(--primary);
  background: #f0f0ff;
}

.book-title {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.book-pages {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.loading-state,
.error-state,
.empty-state {
  padding: 1rem;
  text-align: center;
  color: var(--text-secondary);
}

.retry-btn {
  margin-top: 0.5rem;
  padding: 0.25rem 0.75rem;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.hint {
  font-size: 0.875rem;
  margin-top: 0.25rem;
}
</style>