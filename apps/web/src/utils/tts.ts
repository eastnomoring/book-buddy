/**
 * 按句朗读流水线（Web 端）：
 *   → TTSPlayer 逐句合成并按顺序播放（服务端 DashScope 或浏览器 speechSynthesis）
 *
 * SentenceStreamer / spokenText 已下沉到 @book-buddy/core。
 *
 * 首句在第一个句号出现时就开始合成播放，不用等整段回答生成完，
 * 感知延迟 ≈ 首句 TTS 时间。
 */
import { synthesizeVoice } from '../api/client'
import { spokenText } from '@book-buddy/core'
import { playAudioElement } from './audioPlayback'

/**
 * 朗读队列。useServer=true 时逐句调后端 TTS（音频 mp3 base64）顺序播放；
 * 否则用浏览器 speechSynthesis。每次回答新建一个实例，打断用 stop()。
 */
export class TTSPlayer {
  private queue: Promise<string>[] = []
  private pumping = false
  private stopped = false
  private currentAudio: HTMLAudioElement | null = null

  constructor(private useServer: boolean) {}

  enqueue(sentence: string): void {
    if (this.stopped) return
    const text = spokenText(sentence)
    if (!text) return

    if (this.useServer) {
      // 入队即开始合成，播放时通常已就绪；单句失败跳过不影响后续
      this.queue.push(synthesizeVoice(text).catch(() => ''))
      void this.pump()
    } else {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = 'zh-CN'
      speechSynthesis.speak(utterance)
    }
  }

  /** Z4：播放服务端已合成好的音频（跳过本端 /voice/synthesize HTTP） */
  enqueueAudio(base64: string, mimeType = 'audio/mpeg'): void {
    if (this.stopped || !base64) return
    this.queue.push(Promise.resolve(base64))
    // mimeType 目前播放路径固定 audio/mpeg；若日后扩展可存旁路元数据
    void mimeType
    void this.pump()
  }

  stop(): void {
    this.stopped = true
    this.queue = []
    this.currentAudio?.pause()
    this.currentAudio = null
    if (!this.useServer && 'speechSynthesis' in window) {
      speechSynthesis.cancel()
    }
  }

  private async pump(): Promise<void> {
    if (this.pumping) return
    this.pumping = true
    try {
      while (this.queue.length && !this.stopped) {
        const pending = this.queue.shift()
        if (!pending) continue
        const audioBase64 = await pending
        if (this.stopped) break
        if (audioBase64) await this.playAudio(audioBase64)
      }
    } finally {
      this.pumping = false
    }
  }

  private playAudio(base64: string): Promise<void> {
    const audio = new Audio(`data:audio/mpeg;base64,${base64}`)
    this.currentAudio = audio
    // iOS 微信等自动播放被拦时，等用户点按补播（见 audioPlayback.ts）
    return playAudioElement(audio)
  }
}
