/**
 * 小程序端按句朗读播放器。
 * 复用 core 的 SentenceStreamer / spokenText，逐句调后端 TTS 并顺序播放。
 */
import { SentenceStreamer, spokenText, type ChatMessage } from '@book-buddy/core'
import { synthesizeVoice } from './voice'
import { MpAudioPlayer } from './audioPlayer'

export class MpTTSPlayer {
  private audioPlayer = new MpAudioPlayer()
  private queue: Promise<string>[] = []
  private pumping = false
  private stopped = false
  private streamer: SentenceStreamer
  private playing = false

  constructor(private enabled: boolean) {
    this.streamer = new SentenceStreamer((s) => this.enqueue(s))
  }

  /** 注入流式 delta；会在完整句子形成时自动合成并排队播放 */
  push(delta: string): void {
    if (!this.enabled || this.stopped) return
    this.streamer.push(delta)
  }

  /** 流结束时冲刷残余文本 */
  flush(): void {
    if (!this.enabled || this.stopped) return
    this.streamer.flush()
  }

  /** 直接播放整段文本 */
  playText(text: string): void {
    this.stop()
    if (!this.enabled) return
    this.push(text)
    this.flush()
  }

  stop(): void {
    this.stopped = true
    this.queue = []
    this.audioPlayer.stop()
    this.streamer = new SentenceStreamer((s) => this.enqueue(s))
    this.playing = false
  }

  /** Z4：播放服务端已合成好的音频（跳过本端 /voice/synthesize） */
  enqueueAudio(base64: string, _mimeType = 'audio/mpeg'): void {
    if (this.stopped || !this.enabled || !base64) return
    this.queue.push(Promise.resolve(base64))
    void this.pump()
  }

  private enqueue(sentence: string): void {
    if (this.stopped || !this.enabled) return
    const text = spokenText(sentence)
    if (!text) return

    this.queue.push(
      synthesizeVoice(text).catch((e) => {
        console.error('TTS 合成失败', e)
        return ''
      }),
    )
    void this.pump()
  }

  private async pump(): Promise<void> {
    if (this.pumping) return
    this.pumping = true
    try {
      while (this.queue.length && !this.stopped) {
        const pending = this.queue.shift()
        if (!pending) continue
        const base64 = await pending
        if (this.stopped || !base64) continue
        this.playing = true
        try {
          await this.audioPlayer.play(base64, 'audio/mpeg')
        } catch (e) {
          console.error('TTS 播放失败', e)
        }
        this.playing = false
      }
    } finally {
      this.pumping = false
      this.playing = false
    }
  }
}

/** 辅助：从消息数组里播放最后一条 assistant 消息 */
export function playLastAssistant(
  messages: ChatMessage[],
  player: MpTTSPlayer,
): void {
  const last = messages.slice().reverse().find((m) => m.role === 'assistant')
  if (last) player.playText(last.content)
}
