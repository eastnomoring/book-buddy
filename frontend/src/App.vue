<script setup lang="ts">
import { ref } from 'vue'
import ChatInterface from './components/ChatInterface.vue'
import CameraCapture from './components/CameraCapture.vue'
import BookSelector from './components/BookSelector.vue'
import SettingsPanel from './components/SettingsPanel.vue'

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
        <div class="brand-row">
          <span class="brand-logo" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 6.2C10.4 4.9 8.2 4.3 5.5 4.3c-.6 0-1.2.05-1.8.15v12.6c.6-.1 1.2-.15 1.8-.15 2.7 0 4.9.6 6.5 1.9 1.6-1.3 3.8-1.9 6.5-1.9.6 0 1.2.05 1.8.15V4.45c-.6-.1-1.2-.15-1.8-.15-2.7 0-4.9.6-6.5 1.9Z"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linejoin="round"
              />
              <path d="M12 6.2v12.6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
            </svg>
          </span>
          <p class="brand-mark">Book Buddy</p>
        </div>
        <p class="brand-line">读硬书时的 AI 伴读</p>
      </div>
      <div class="masthead-actions">
        <BookSelector @select="onBookSelected" />
        <SettingsPanel />
      </div>
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
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.5rem;
  margin: -1.5rem -1.25rem 1.5rem;
  padding: 1.1rem 1.25rem 1.15rem;
  border-bottom: 1px solid var(--line);
  background: rgba(240, 244, 246, 0.72);
  backdrop-filter: blur(16px) saturate(1.15);
  -webkit-backdrop-filter: blur(16px) saturate(1.15);
  animation: rise-in 0.7s var(--ease);
}

.brand-block {
  min-width: 0;
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}

.brand-logo {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 12px;
  color: #f2fffa;
  background: var(--accent-gradient);
  box-shadow: var(--shadow-accent), inset 0 1px 0 rgba(255, 255, 255, 0.22);
}

.brand-mark {
  font-family: var(--font-display);
  font-size: clamp(2rem, 4vw, 2.9rem);
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

.masthead-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
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
