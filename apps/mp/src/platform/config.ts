/**
 * 小程序端后端地址配置。
 * 开发期默认连本地 FastAPI（http://localhost:8000/api），
 * 可在页面设置里修改，也可以通过微信开发者工具修改 Storage。
 */
const DEFAULT_API_BASE = 'http://localhost:8000/api'
const API_BASE_KEY = 'bb_api_base'

export function getApiBase(): string {
  try {
    const saved = uni.getStorageSync(API_BASE_KEY)
    if (saved) return String(saved)
  } catch {
    // storage 不可用时回退默认值
  }
  return DEFAULT_API_BASE
}

export function setApiBase(base: string): void {
  uni.setStorageSync(API_BASE_KEY, base)
}


import {
  API_PATHS,
  mapConfig,
  mapTestResult,
  PlatformError,
  type AppConfig,
  type ConfigTestResult,
  type ConfigUpdatePayload,
} from '@book-buddy/core'

export function getConfig(): Promise<AppConfig> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: getApiBase() + API_PATHS.CONFIG,
      method: 'GET',
      success: (res) => {
        const status = res.statusCode ?? 0
        if (status < 200 || status >= 300) {
          reject(new PlatformError(`HTTP ${status}`))
          return
        }
        resolve(mapConfig(res.data as Record<string, unknown>))
      },
      fail: (err) => reject(new PlatformError(err.errMsg || 'get config failed', err)),
    })
  })
}

export function updateConfig(payload: ConfigUpdatePayload): Promise<AppConfig> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: getApiBase() + API_PATHS.CONFIG,
      method: 'PUT',
      header: { 'Content-Type': 'application/json' },
      data: {
        provider: payload.provider,
        api_key: payload.apiKey || undefined,
        base_url: payload.baseUrl || undefined,
        model: payload.model || undefined,
        voice_api_key: payload.voiceApiKey || undefined,
      },
      success: (res) => {
        const status = res.statusCode ?? 0
        if (status < 200 || status >= 300) {
          reject(new PlatformError(`HTTP ${status}`))
          return
        }
        resolve(mapConfig(res.data as Record<string, unknown>))
      },
      fail: (err) => reject(new PlatformError(err.errMsg || 'update config failed', err)),
    })
  })
}

export function testConfigConnection(payload: ConfigUpdatePayload): Promise<ConfigTestResult> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: getApiBase() + API_PATHS.CONFIG_TEST,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: {
        provider: payload.provider,
        api_key: payload.apiKey || undefined,
        base_url: payload.baseUrl || undefined,
        model: payload.model || undefined,
      },
      success: (res) => {
        const status = res.statusCode ?? 0
        if (status < 200 || status >= 300) {
          reject(new PlatformError(`HTTP ${status}`))
          return
        }
        resolve(mapTestResult(res.data as Record<string, unknown>))
      },
      fail: (err) => reject(new PlatformError(err.errMsg || 'test config failed', err)),
    })
  })
}
