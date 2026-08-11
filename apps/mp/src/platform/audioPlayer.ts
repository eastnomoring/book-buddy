/**
 * 微信小程序端 AudioPlayer 实现。
 * 使用 InnerAudioContext 播放 base64 音频；
 * 超过阈值时先把 base64 写入临时文件，再让 src 指向本地路径，规避超长 data URI 不稳定问题。
 */
import { PlatformError, type AudioPlayer } from '@book-buddy/core'
import { writeFileBase64, removeFile } from './fs'

const DATA_URI_THRESHOLD = 256 * 1024 // 256KB（base64 字符数）

export class MpAudioPlayer implements AudioPlayer {
  private ctx: WechatMiniprogram.InnerAudioContext | null = null
  private tempFilePath: string | null = null

  async play(base64: string, mimeType: string): Promise<void> {
    this.stop()

    let src = ''
    if (base64.length > DATA_URI_THRESHOLD && mimeType === 'audio/mpeg') {
      // 长音频落临时文件
      const filePath = `${wx.env.USER_DATA_PATH}/book_buddy_tts_${Date.now()}.mp3`
      await writeFileBase64(filePath, base64)
      this.tempFilePath = filePath
      src = filePath
    } else {
      src = `data:${mimeType};base64,${base64}`
    }

    return new Promise((resolve, reject) => {
      const ctx = wx.createInnerAudioContext()
      this.ctx = ctx
      ctx.src = src

      const cleanupAndResolve = () => {
        this.cleanupTempFile()
        resolve()
      }
      const cleanupAndReject = (err: { errMsg?: string }) => {
        this.cleanupTempFile()
        reject(new PlatformError(err.errMsg || 'audio play failed', err))
      }

      ctx.onEnded(cleanupAndResolve)
      ctx.onError(cleanupAndReject)
      ctx.onStop(cleanupAndResolve)

      ctx.play()
    })
  }

  stop(): void {
    try {
      this.ctx?.stop()
    } catch {
      // ignore
    }
    this.ctx?.destroy()
    this.ctx = null
    this.cleanupTempFile()
  }

  private cleanupTempFile() {
    if (this.tempFilePath) {
      void removeFile(this.tempFilePath)
      this.tempFilePath = null
    }
  }
}
