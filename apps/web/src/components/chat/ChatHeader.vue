<script setup lang="ts">
defineProps<{
  bookId?: string | null
  pageNumber?: number
  hasPendingImage: boolean
  speakerOn: boolean
}>()

const emit = defineEmits<{
  toggleSpeaker: []
}>()
</script>

<template>
  <div class="chat-top">
    <div>
      <h2 class="pane-title">问答</h2>
      <p class="pane-sub">结合书页与知识库，按书中符号体系讲解</p>
    </div>
    <div class="status-row">
      <span v-if="bookId" class="status"><i class="dot" aria-hidden="true"></i>已关联书籍</span>
      <span v-if="pageNumber" class="status tone"><i class="dot" aria-hidden="true"></i>第 {{ pageNumber }} 页</span>
      <span v-if="hasPendingImage" class="status pending"><i class="dot" aria-hidden="true"></i>待发送图片</span>
      <button
        type="button"
        class="speaker-btn"
        :class="{ muted: !speakerOn }"
        @click="emit('toggleSpeaker')"
        :title="speakerOn ? '关闭朗读' : '开启朗读'"
        :aria-label="speakerOn ? '关闭朗读' : '开启朗读'"
      >
        <svg v-if="speakerOn" width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M11 5 6.5 9H3v6h3.5L11 19V5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
          <path d="M15 9a4 4 0 0 1 0 6M17.5 6.5a7.5 7.5 0 0 1 0 11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
        </svg>
        <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M11 5 6.5 9H3v6h3.5L11 19V5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
          <path d="m16 9 5 6m0-6-5 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding-bottom: 0.95rem;
  border-bottom: 1px solid var(--line);
}

.pane-title {
  font-family: var(--font-display);
  font-size: 1.45rem;
  font-weight: 400;
  line-height: 1.1;
}

.pane-sub {
  margin-top: 0.3rem;
  font-size: 0.82rem;
  color: var(--muted);
}

.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  justify-content: flex-end;
}

.status {
  display: inline-flex;
  align-items: center;
  gap: 0.32rem;
  font-size: 0.72rem;
  letter-spacing: 0.04em;
  padding: 0.3rem 0.62rem;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-deep);
  border: 1px solid rgba(26, 107, 92, 0.18);
}

.status .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
}

.status.tone {
  background: rgba(21, 32, 40, 0.06);
  color: var(--ink-soft);
  border-color: rgba(21, 32, 40, 0.1);
}

.status.tone .dot {
  background: var(--muted);
}

.status.pending {
  background: var(--warn-soft);
  color: var(--warn);
  border-color: rgba(154, 91, 26, 0.2);
}

.status.pending .dot {
  background: var(--warn);
  animation: pulse-soft 1.4s ease-in-out infinite;
}

.speaker-btn {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  color: var(--accent-deep);
  cursor: pointer;
  transition: border-color 0.2s var(--ease), background 0.2s var(--ease),
    transform 0.2s var(--ease), box-shadow 0.2s var(--ease);
}

.speaker-btn:hover {
  border-color: var(--line-strong);
  background: #fff;
  transform: translateY(-1px);
  box-shadow: var(--shadow-lift);
}

.speaker-btn.muted {
  color: var(--muted);
}
</style>
