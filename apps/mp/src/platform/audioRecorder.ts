/**
 * 微信小程序端 AudioRecorder 实现。
 * 使用 RecorderManager 录制 16kHz 单声道 WAV，与后端 ASR 契约对齐。
 */
import {
  PlatformError,
  type AudioRecorder,
  type AudioRecordResult,
} from '@book-buddy/core'
import { readFileBase64 } from './fs'

export class MpAudioRecorder implements AudioRecorder {
  private recorder = wx.getRecorderManager()
  private startResolve: (() => void) | null = null
  private startReject: ((err: PlatformError) => void) | null = null
  private stopResolve: ((result: AudioRecordResult) => void) | null = null
  private stopReject: ((err: PlatformError) => void) | null = null
  private cancelled = false

  constructor() {
    this.recorder.onStart(() => {
      this.startResolve?.()
      this.startResolve = null
      this.startReject = null
    })

    this.recorder.onError((err) => {
      this.startReject?.(new PlatformError(err.errMsg || 'recorder error', err))
      this.stopReject?.(new PlatformError(err.errMsg || 'recorder error', err))
      this.cleanup()
    })

    this.recorder.onStop((res) => {
      if (this.cancelled) {
        this.cleanup()
        return
      }
      this.handleStop(res.tempFilePath)
    })
  }

  start(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.cancelled = false
      this.startResolve = resolve
      this.startReject = reject
      this.recorder.start({
        duration: 60000,
        sampleRate: 16000,
        numberOfChannels: 1,
        encodeBitRate: 256000,
        format: 'wav',
      })
    })
  }

  stop(): Promise<AudioRecordResult> {
    return new Promise((resolve, reject) => {
      this.stopResolve = resolve
      this.stopReject = reject
      this.recorder.stop()
    })
  }

  cancel(): void {
    this.cancelled = true
    this.recorder.stop()
  }

  private async handleStop(tempFilePath: string) {
    try {
      const base64 = await readFileBase64(tempFilePath)
      const result: AudioRecordResult = {
        base64,
        mimeType: 'audio/wav',
        sampleRate: 16000,
      }
      this.stopResolve?.(result)
    } catch (e) {
      this.stopReject?.(
        e instanceof PlatformError
          ? e
          : new PlatformError(e instanceof Error ? e.message : 'read audio failed', e),
      )
    } finally {
      this.cleanup()
    }
  }

  private cleanup() {
    this.startResolve = null
    this.startReject = null
    this.stopResolve = null
    this.stopReject = null
  }
}
