<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getApiBase,
  setApiBase,
  getConfig,
  updateConfig,
  testConfigConnection,
} from '../../platform/config'
import type { AppConfig, ConfigTestResult, ConfigUpdatePayload } from '@book-buddy/core'

type PresetKey = 'zhipu' | 'qwen' | 'custom'

const PRESETS: Record<
  PresetKey,
  { label: string; provider: string; baseUrl: string; model: string; hint: string }
> = {
  zhipu: {
    label: '智谱 GLM',
    provider: 'openai',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4/',
    model: 'glm-4.6v',
    hint: 'open.bigmodel.cn 创建 Key，glm-4.6v 支持识图',
  },
  qwen: {
    label: '通义千问（百炼）',
    provider: 'qwen',
    baseUrl: '',
    model: 'qwen-vl-max',
    hint: 'bailian.console.aliyun.com 创建 Key，与语音 Key 相同',
  },
  custom: {
    label: '自定义（OpenAI 兼容）',
    provider: 'openai',
    baseUrl: '',
    model: '',
    hint: '硅基流动 / Ollama 等，填写 Base URL 与模型名',
  },
}
const PRESET_KEYS: PresetKey[] = ['zhipu', 'qwen', 'custom']
const PRESET_LABELS = PRESET_KEYS.map((k) => PRESETS[k].label)

const apiBase = ref(getApiBase())
const config = ref<AppConfig | null>(null)

const preset = ref<PresetKey>('zhipu')
const apiKey = ref('')
const baseUrl = ref(PRESETS.zhipu.baseUrl)
const model = ref(PRESETS.zhipu.model)
const voiceApiKey = ref('')

const saving = ref(false)
const testing = ref(false)
const testResult = ref<ConfigTestResult | null>(null)
const message = ref('')

function inferPreset(provider: string, url?: string): PresetKey {
  if (provider === 'qwen') return 'qwen'
  if (url && url.includes('bigmodel.cn')) return 'zhipu'
  if (!url) return 'zhipu'
  return 'custom'
}

onMounted(async () => {
  try {
    const cfg = await getConfig()
    config.value = cfg
    const p = inferPreset(cfg.provider, cfg.baseUrl)
    preset.value = p
    baseUrl.value = cfg.baseUrl || PRESETS[p].baseUrl
    model.value = cfg.model || PRESETS[p].model
  } catch {
    message.value = '获取后端配置失败，请检查后端地址'
  }
})

function onPresetChange(e: { detail: { value: string | number } }) {
  const key = PRESET_KEYS[Number(e.detail.value)] ?? 'zhipu'
  preset.value = key
  baseUrl.value = PRESETS[key].baseUrl
  model.value = PRESETS[key].model
  testResult.value = null
}

function saveApiBase(): boolean {
  const base = apiBase.value.trim()
  if (!base) {
    message.value = '后端地址不能为空'
    return false
  }
  setApiBase(base.endsWith('/api') ? base : base.replace(/\/$/, '') + '/api')
  return true
}

function payload(): ConfigUpdatePayload {
  return {
    provider: PRESETS[preset.value].provider,
    apiKey: apiKey.value || undefined,
    baseUrl: preset.value === 'qwen' ? undefined : baseUrl.value || undefined,
    model: model.value || undefined,
    voiceApiKey: voiceApiKey.value || undefined,
  }
}

async function handleTest() {
  testing.value = true
  testResult.value = null
  message.value = ''
  try {
    testResult.value = await testConfigConnection(payload())
  } catch {
    testResult.value = { ok: false, message: '请求失败，请确认后端地址可访问' }
  } finally {
    testing.value = false
  }
}

async function handleSave() {
  if (!saveApiBase()) return
  saving.value = true
  message.value = ''
  try {
    config.value = await updateConfig(payload())
    apiKey.value = ''
    voiceApiKey.value = ''
    message.value = '已保存，立即生效'
  } catch {
    message.value = '保存失败，请确认后端已启动'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <view class="page">
    <view class="card">
      <text class="title">后端地址</text>
      <input v-model="apiBase" class="input" placeholder="http://localhost:8000/api" />
      <text class="hint">微信开发者工具需勾选「不校验合法域名」；真机需与后端同一局域网</text>
    </view>

    <view class="card">
      <text class="title">模型设置</text>
      <view v-if="config && !config.configured" class="notice">
        还没有配置 API Key，填写后保存即可开始使用。
      </view>

      <text class="field-label">提供商</text>
      <picker
        class="picker"
        mode="selector"
        :range="PRESET_LABELS"
        :value="PRESET_KEYS.indexOf(preset)"
        @change="onPresetChange"
      >
        <view class="picker-value">{{ PRESETS[preset].label }}</view>
      </picker>
      <text class="hint">{{ PRESETS[preset].hint }}</text>

      <text class="field-label">API Key</text>
      <input
        v-model="apiKey"
        class="input"
        password
        :placeholder="config?.apiKeyMasked ? `已保存 ${config.apiKeyMasked}，留空则不修改` : '粘贴你的 API Key'"
      />

      <template v-if="preset !== 'qwen'">
        <text class="field-label">Base URL</text>
        <input v-model="baseUrl" class="input" placeholder="https://..." />
      </template>

      <text class="field-label">模型</text>
      <input v-model="model" class="input" placeholder="模型名称" />
    </view>

    <view class="card">
      <text class="title">语音服务（DashScope）</text>
      <text class="field-label">语音 API Key</text>
      <input
        v-model="voiceApiKey"
        class="input"
        password
        :placeholder="config?.voiceApiKeyMasked ? `已保存 ${config.voiceApiKeyMasked}，留空则不修改` : 'bailian.console.aliyun.com 创建 Key'"
      />
      <text class="hint">用于语音识别与朗读。通义千问的 Key 与语音 Key 相同，上方填过即可。</text>
    </view>

    <view class="actions">
      <button class="btn ghost" :disabled="testing" @click="handleTest">
        {{ testing ? '测试中…' : '测试连接' }}
      </button>
      <button class="btn primary" :disabled="saving" @click="handleSave">
        {{ saving ? '保存中…' : '保存' }}
      </button>
    </view>

    <view v-if="testResult" class="card result" :class="{ ok: testResult.ok }">
      <text class="result-text">{{ testResult.ok ? '✓ ' : '✗ ' }}{{ testResult.message }}</text>
    </view>
    <text v-if="message" class="message">{{ message }}</text>

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

.notice {
  margin-bottom: 0.75rem;
  padding: 0.6rem 0.75rem;
  border-radius: 10px;
  border: 1px solid rgba(26, 107, 92, 0.2);
  background: rgba(26, 107, 92, 0.06);
  font-size: 0.82rem;
  color: #145447;
}

.field-label {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.72rem;
  color: #6b7884;
}

.input {
  padding: 0.55rem 0.75rem;
  border: 1px solid rgba(21, 32, 40, 0.12);
  border-radius: 10px;
  background: #fff;
  font-size: 0.88rem;
  margin-bottom: 0.6rem;
}

.picker-value {
  padding: 0.55rem 0.75rem;
  border: 1px solid rgba(21, 32, 40, 0.12);
  border-radius: 10px;
  background: #fff;
  font-size: 0.88rem;
}

.hint {
  display: block;
  font-size: 0.72rem;
  color: #6b7884;
  margin: 0.4rem 0 0.6rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.btn {
  padding: 0.55rem 0.95rem;
  border-radius: 10px;
  font-size: 0.85rem;
}

.btn.primary {
  color: #f7fffc;
  background: linear-gradient(135deg, #22907b 0%, #1a6b5c 55%, #145447 100%);
}

.btn.ghost {
  border: 1px solid rgba(21, 32, 40, 0.12);
  background: rgba(255, 255, 255, 0.6);
  color: #152028;
}

.result {
  background: rgba(180, 35, 24, 0.06);
}

.result.ok {
  background: rgba(26, 107, 92, 0.06);
}

.result-text {
  font-size: 0.82rem;
  color: #b42318;
  word-break: break-all;
}

.result.ok .result-text {
  color: #145447;
}

.message {
  display: block;
  margin: 0 0 1rem;
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
