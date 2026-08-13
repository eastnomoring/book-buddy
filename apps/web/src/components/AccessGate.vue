<script setup lang="ts">
/**
 * 访问口令弹窗：后端开启 AUTH_TOKEN 后，首次访问或 401 时展示。
 * 验证方式：拿候选口令试调 /api/config，通过则落 localStorage 并解锁。
 */
import { ref } from 'vue'
import axios from 'axios'
import { API_PATHS } from '@book-buddy/core'
import { setAuthToken } from '../utils/auth'

const emit = defineEmits<{
  unlocked: []
}>()

const token = ref('')
const checking = ref(false)
const error = ref('')

async function submit() {
  const candidate = token.value.trim()
  if (!candidate) {
    error.value = '请输入访问口令'
    return
  }
  checking.value = true
  error.value = ''
  try {
    await axios.get('/api' + API_PATHS.CONFIG, {
      headers: { Authorization: `Bearer ${candidate}` },
      timeout: 10000,
    })
    setAuthToken(candidate)
    emit('unlocked')
  } catch (e) {
    error.value =
      axios.isAxiosError(e) && e.response?.status === 401
        ? '口令不正确，请重试'
        : '无法连接后端，请稍后再试'
  } finally {
    checking.value = false
  }
}
</script>

<template>
  <div class="gate">
    <div class="gate-card">
      <p class="gate-title">需要访问口令</p>
      <p class="gate-copy">该站点已开启访问保护，请输入口令继续使用。</p>
      <input
        v-model="token"
        class="gate-input"
        type="password"
        placeholder="访问口令"
        autocomplete="off"
        @keyup.enter="submit"
      />
      <button class="btn btn-primary gate-btn" :disabled="checking" @click="submit">
        {{ checking ? '验证中…' : '进入' }}
      </button>
      <p v-if="error" class="gate-error">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.gate {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 1.5rem;
  background: linear-gradient(165deg, #f4f7f8 0%, #eef2f4 42%, #e2e8ec 100%);
}

.gate-card {
  width: min(360px, 100%);
  padding: 1.75rem;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--shadow-pop);
  text-align: center;
}

.gate-title {
  font-family: var(--font-display);
  font-size: 1.4rem;
  color: var(--ink);
  margin-bottom: 0.4rem;
}

.gate-copy {
  font-size: 0.86rem;
  color: var(--muted);
  margin-bottom: 1rem;
}

.gate-input {
  margin-bottom: 0.75rem;
  text-align: center;
}

.gate-btn {
  width: 100%;
}

.gate-error {
  margin-top: 0.65rem;
  font-size: 0.82rem;
  color: var(--error);
}
</style>
