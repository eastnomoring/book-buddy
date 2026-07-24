<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import {
  getConfig,
  updateConfig,
  testConfig,
  type ConfigTestResult,
} from '../api/client'

type PresetKey = 'zhipu' | 'qwen' | 'custom'

const PRESETS: Record<PresetKey, { label: string; provider: string; baseUrl: string; model: string; hint: string }> = {
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
    hint: 'bailian.console.aliyun.com 创建 Key',
  },
  custom: {
    label: '自定义（OpenAI 兼容）',
    provider: 'openai',
    baseUrl: '',
    model: '',
    hint: '硅基流动 / Ollama 等，填写 base_url 与模型名',
  },
}

const open = ref(false)
const rootEl = ref<HTMLElement | null>(null)

const preset = ref<PresetKey>('zhipu')
const apiKey = ref('')
const baseUrl = ref(PRESETS.zhipu.baseUrl)
const model = ref(PRESETS.zhipu.model)
const savedKeyMasked = ref('')
const configured = ref(false)

const saving = ref(false)
const testing = ref(false)
const testResult = ref<ConfigTestResult | null>(null)
const saveMessage = ref<string | null>(null)

function applyPreset(key: PresetKey) {
  preset.value = key
  baseUrl.value = PRESETS[key].baseUrl
  model.value = PRESETS[key].model
  testResult.value = null
}

function inferPreset(provider: string, url?: string): PresetKey {
  if (provider === 'qwen') return 'qwen'
  if (url && url.includes('bigmodel.cn')) return 'zhipu'
  if (!url) return 'zhipu'
  return 'custom'
}

async function load() {
  try {
    const cfg = await getConfig()
    configured.value = cfg.configured
    savedKeyMasked.value = cfg.apiKeyMasked
    const p = inferPreset(cfg.provider, cfg.baseUrl)
    preset.value = p
    baseUrl.value = cfg.baseUrl || PRESETS[p].baseUrl
    model.value = cfg.model || PRESETS[p].model
    if (!cfg.configured) open.value = true
  } catch (e) {
    console.error('加载配置失败', e)
  }
}

function payload() {
  return {
    provider: PRESETS[preset.value].provider,
    apiKey: apiKey.value || undefined,
    baseUrl: preset.value === 'qwen' ? undefined : baseUrl.value || undefined,
    model: model.value || undefined,
  }
}

async function handleTest() {
  testing.value = true
  testResult.value = null
  saveMessage.value = null
  try {
    testResult.value = await testConfig(payload())
  } catch (e) {
    testResult.value = { ok: false, message: '请求失败，请确认后端已启动' }
    console.error(e)
  } finally {
    testing.value = false
  }
}

async function handleSave() {
  saving.value = true
  saveMessage.value = null
  try {
    const cfg = await updateConfig(payload())
    configured.value = cfg.configured
    savedKeyMasked.value = cfg.apiKeyMasked
    apiKey.value = ''
    saveMessage.value = '已保存，立即生效'
  } catch (e) {
    saveMessage.value = '保存失败'
    console.error(e)
  } finally {
    saving.value = false
  }
}

function onDocClick(e: MouseEvent) {
  if (!rootEl.value) return
  if (!rootEl.value.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => {
  load()
  document.addEventListener('click', onDocClick)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
})
</script>

<template>
  <div class="settings" ref="rootEl">
    <button
      class="gear"
      :class="{ warn: !configured }"
      type="button"
      @click="open = !open"
      :aria-expanded="open"
      :title="configured ? '模型设置' : '请先配置 API Key'"
    >
      ⚙<span v-if="!configured" class="gear-badge">!</span>
    </button>

    <div v-if="open" class="panel">
      <p class="panel-title">模型设置</p>

      <div v-if="!configured" class="notice">还没有配置 API Key，填写后保存即可开始使用。</div>

      <label class="field">
        <span class="field-label">提供商</span>
        <select :value="preset" @change="applyPreset(($event.target as HTMLSelectElement).value as PresetKey)">
          <option v-for="(p, key) in PRESETS" :key="key" :value="key">{{ p.label }}</option>
        </select>
      </label>
      <p class="field-hint">{{ PRESETS[preset].hint }}</p>

      <label class="field">
        <span class="field-label">API Key</span>
        <input
          v-model="apiKey"
          type="password"
          :placeholder="savedKeyMasked ? `已保存 ${savedKeyMasked}，留空则不修改` : '粘贴你的 API Key'"
          autocomplete="off"
        />
      </label>

      <label v-if="preset !== 'qwen'" class="field">
        <span class="field-label">Base URL</span>
        <input v-model="baseUrl" type="text" placeholder="https://..." />
      </label>

      <label class="field">
        <span class="field-label">模型</span>
        <input v-model="model" type="text" placeholder="模型名称" />
      </label>

      <div class="actions">
        <button type="button" class="btn ghost" :disabled="testing" @click="handleTest">
          {{ testing ? '测试中…' : '测试连接' }}
        </button>
        <button type="button" class="btn primary" :disabled="saving" @click="handleSave">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </div>

      <p v-if="testResult" class="result" :class="{ ok: testResult.ok }">
        {{ testResult.ok ? '✓ ' : '✗ ' }}{{ testResult.message }}
      </p>
      <p v-if="saveMessage" class="result ok">{{ saveMessage }}</p>
    </div>
  </div>
</template>

<style scoped>
.settings {
  position: relative;
  flex-shrink: 0;
}

.gear {
  position: relative;
  width: 2.5rem;
  height: 2.5rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.7);
  font-size: 1.1rem;
  transition: border-color 0.2s var(--ease), background 0.2s var(--ease);
}

.gear:hover {
  border-color: var(--line-strong);
  background: #fff;
}

.gear.warn {
  border-color: var(--error);
}

.gear-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--error);
  color: #fff;
  font-size: 0.62rem;
  line-height: 14px;
  text-align: center;
}

.panel {
  position: absolute;
  top: calc(100% + 0.45rem);
  right: 0;
  z-index: 30;
  width: min(360px, 90vw);
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.97);
  box-shadow: var(--shadow-soft);
  animation: rise-in 0.25s var(--ease);
}

.panel-title {
  font-weight: 600;
  margin-bottom: 0.75rem;
}

.notice {
  margin-bottom: 0.75rem;
  padding: 0.55rem 0.7rem;
  border-radius: 6px;
  background: var(--accent-soft);
  font-size: 0.82rem;
  color: var(--ink);
}

.field {
  display: block;
  margin-bottom: 0.65rem;
}

.field-label {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}

.field input,
.field select {
  width: 100%;
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
  font-size: 0.88rem;
}

.field input:focus,
.field select:focus {
  outline: none;
  border-color: var(--accent);
}

.field-hint {
  margin: -0.35rem 0 0.65rem;
  font-size: 0.75rem;
  color: var(--muted);
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 0.85rem;
}

.btn {
  padding: 0.5rem 0.9rem;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s var(--ease);
}

.btn.primary {
  background: var(--accent);
  color: #f7fffc;
}

.btn.primary:hover:not(:disabled) {
  background: var(--accent-deep);
}

.btn.ghost {
  border: 1px solid var(--line);
  background: transparent;
}

.btn.ghost:hover:not(:disabled) {
  border-color: var(--line-strong);
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.result {
  margin-top: 0.65rem;
  font-size: 0.82rem;
  color: var(--error);
  word-break: break-all;
}

.result.ok {
  color: var(--accent-deep);
}
</style>
