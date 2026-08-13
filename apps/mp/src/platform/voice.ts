/**
 * 语音相关后端调用（TTS / ASR）。
 * 后端 /voice/transcribe 与 /voice/synthesize 都接收/返回 JSON，
 * 因此这里用 uni.request，而非 wx.uploadFile。
 */
import {
  API_PATHS,
  PlatformError,
  type VoiceTranscribeResponse,
} from '@book-buddy/core'
import { getApiBase } from './config'

export function transcribeVoice(
  audioBase64: string,
  format: string = 'wav',
): Promise<VoiceTranscribeResponse> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: getApiBase() + API_PATHS.VOICE_TRANSCRIBE,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { audio: audioBase64, format },
      success: (res) => {
        const status = res.statusCode ?? 0
        if (status < 200 || status >= 300) {
          reject(new PlatformError(`HTTP ${status}`))
          return
        }
        resolve(res.data as VoiceTranscribeResponse)
      },
      fail: (err) => reject(new PlatformError(err.errMsg || 'transcribe failed', err)),
    })
  })
}

export function synthesizeVoice(text: string, voice?: string): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: getApiBase() + API_PATHS.VOICE_SYNTHESIZE,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { text, voice },
      success: (res) => {
        const status = res.statusCode ?? 0
        if (status < 200 || status >= 300) {
          reject(new PlatformError(`HTTP ${status}`))
          return
        }
        const data = res.data as { audio: string }
        resolve(data.audio)
      },
      fail: (err) => reject(new PlatformError(err.errMsg || 'synthesize failed', err)),
    })
  })
}
