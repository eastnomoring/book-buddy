<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getApiBase, setApiBase, getConfig } from '../../platform/config'
import type { AppConfig } from '@book-buddy/core'

const apiBase = ref(getApiBase())
const config = ref<AppConfig | null>(null)
const loading = ref(false)
const message = ref('')

onMounted(async () => {
  loading.value = true
  try {
    config.value = await getConfig()
  } catch {
    message.value = '获取后端配置失败，请检查 baseURL'
  } finally {
    loading.value = false
  }
})

function save() {
  const base = apiBase.value.trim()
  if (!base) {
    message.value = 'baseURL 不能为空'
    return
  }
  setApiBase(base.endsWith('/api') ? base : base.replace(/\/$/, '') + '/api')
  message.value = '已保存'
  setTimeout(() => uni.navigateBack(), 600)
}
</script>

<template>
  <view class="page">
    <view class="card">
      <text class="title">后端地址</text>
      <input v-model="apiBase" class="input" placeholder="http://localhost:8000/api" />
      <text class="hint">微信开发者工具需勾选「不校验合法域名」</text>
      <button class="save" @click="save">保存</button>
      <text v-if="message" class="message">{{ message }}</text>
    </view>

    <view v-if="config" class="card">
      <text class="title">当前后端配置</text>
      <view class="row">
        <text class="label">Provider</text>
        <text class="value">{{ config.provider }}</text>
      </view>
      <view class="row">
        <text class="label">Model</text>
        <text class="value">{{ config.model }}</text>
      </view>
      <view class="row">
        <text class="label">已配置 LLM</text>
        <text class="value">{{ config.configured ? '是' : '否' }}</text>
      </view>
      <view class="row">
        <text class="label">已配置语音</text>
        <text class="value">{{ config.voiceConfigured ? '是' : '否' }}</text>
      </view>
    </view>

    <view v-else-if="loading" class="card">
      <text class="hint">正在加载后端配置…</text>
    </view>
  </view>
</template>

<style scoped>
.page {
  min-height: 100vh;
  padding: 1rem;
  background: linear-gradient(165deg, #f4f7f8 0%, #eef2f4 42%, #e2e8ec 100%);
}

.card {
  margin-bottom: 1rem;
  padding: 1rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(21, 32, 40, 0.1);
}

.title {
  display: block;
  font-size: 0.95rem;
  font-weight: 500;
  color: #152028;
  margin-bottom: 0.6rem;
}

.input {
  padding: 0.55rem 0.75rem;
  border: 1px solid rgba(21, 32, 40, 0.12);
  border-radius: 10px;
  background: #fff;
  font-size: 0.88rem;
  margin-bottom: 0.4rem;
}

.hint {
  display: block;
  font-size: 0.72rem;
  color: #6b7884;
  margin-bottom: 0.8rem;
}

.save {
  padding: 0.55rem 0;
  border-radius: 10px;
  font-size: 0.9rem;
  color: #f7fffc;
  background: linear-gradient(135deg, #22907b 0%, #1a6b5c 55%, #145447 100%);
}

.message {
  display: block;
  margin-top: 0.6rem;
  font-size: 0.82rem;
  color: #1a6b5c;
}

.row {
  display: flex;
  justify-content: space-between;
  padding: 0.45rem 0;
  border-bottom: 1px solid rgba(21, 32, 40, 0.06);
}

.row:last-child {
  border-bottom: none;
}

.label {
  font-size: 0.82rem;
  color: #6b7884;
}

.value {
  font-size: 0.82rem;
  color: #152028;
}
</style>
