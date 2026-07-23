<script setup lang="ts">
import { ref } from 'vue'
import ChatInterface from './components/ChatInterface.vue'
import CameraCapture from './components/CameraCapture.vue'
import BookSelector from './components/BookSelector.vue'

const currentBookId = ref<string | null>(null)
const currentPage = ref<number>(1)
const capturedImage = ref<string | null>(null)

function onBookSelected(bookId: string) {
  currentBookId.value = bookId
}

function onPageChange(page: number) {
  currentPage.value = page
}

function onImageCaptured(imageBase64: string) {
  capturedImage.value = imageBase64
}
</script>

<template>
  <div class="app">
    <header class="header">
      <div class="container header-content">
        <h1 class="logo">
          <span class="logo-icon">📚</span>
          Book Buddy
        </h1>
        <BookSelector @select="onBookSelected" />
      </div>
    </header>

    <main class="main container">
      <div class="workspace">
        <aside class="sidebar">
          <CameraCapture 
            @capture="onImageCaptured"
            :currentPage="currentPage"
            @pageChange="onPageChange"
          />
        </aside>

        <section class="chat-area">
          <ChatInterface 
            :bookId="currentBookId"
            :image="capturedImage"
            @clearImage="capturedImage = null"
          />
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 1rem 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.logo {
  font-size: 1.5rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.logo-icon {
  font-size: 1.75rem;
}

.main {
  flex: 1;
  padding: 2rem 1rem;
}

.workspace {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1.5rem;
  min-height: calc(100vh - 200px);
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.chat-area {
  display: flex;
  flex-direction: column;
}

@media (max-width: 768px) {
  .workspace {
    grid-template-columns: 1fr;
  }
  
  .header-content {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>