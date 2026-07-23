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
    <header class="masthead">
      <div class="brand-block">
        <p class="brand-mark">Book Buddy</p>
        <p class="brand-line">读硬书时的 AI 伴读</p>
      </div>
      <BookSelector @select="onBookSelected" />
    </header>

    <main class="stage">
      <aside class="capture-pane">
        <CameraCapture
          @capture="onImageCaptured"
          @clear="capturedImage = null"
          :currentPage="currentPage"
          @pageChange="onPageChange"
        />
      </aside>

      <section class="dialogue-pane">
        <ChatInterface
          :bookId="currentBookId"
          :image="capturedImage"
          :pageNumber="currentPage"
          @clearImage="capturedImage = null"
        />
      </section>
    </main>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  max-width: 1280px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 2rem;
  animation: fade-in 0.6s var(--ease);
}

.masthead {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.5rem;
  padding-bottom: 1.35rem;
  border-bottom: 1px solid var(--line);
  margin-bottom: 1.5rem;
  animation: rise-in 0.7s var(--ease);
}

.brand-block {
  min-width: 0;
}

.brand-mark {
  font-family: var(--font-display);
  font-size: clamp(2.4rem, 4.5vw, 3.4rem);
  line-height: 1;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.brand-line {
  margin-top: 0.45rem;
  font-size: 0.95rem;
  font-weight: 400;
  color: var(--muted);
  letter-spacing: 0.02em;
}

.stage {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(280px, 360px) 1fr;
  gap: 1.25rem;
  min-height: calc(100vh - 180px);
  animation: rise-in 0.85s var(--ease) 0.08s both;
}

.capture-pane,
.dialogue-pane {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

@media (max-width: 900px) {
  .masthead {
    flex-direction: column;
    align-items: stretch;
  }

  .stage {
    grid-template-columns: 1fr;
    min-height: auto;
  }
}
</style>
