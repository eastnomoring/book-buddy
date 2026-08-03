/**
 * 按句朗读流水线：
 *   SentenceStreamer 把 LLM 的 SSE 增量文本切成完整句子
 *   → TTSPlayer 逐句合成并按顺序播放（服务端 DashScope 或浏览器 speechSynthesis）
 *
 * 首句在第一个句号出现时就开始合成播放，不用等整段回答生成完，
 * 感知延迟 ≈ 首句 TTS 时间。
 */
import { synthesizeVoice } from '../api/client'

/** 把 LLM 增量文本切成完整句子（句读点：。!?!；;\n） */
export class SentenceStreamer {
  private buffer = ''

  constructor(private onSentence: (sentence: string) => void) {}

  push(delta: string): void {
    this.buffer += delta
    let end = this.findSentenceEnd()
    while (end >= 0) {
      const sentence = this.buffer.slice(0, end + 1).trim()
      if (sentence) this.onSentence(sentence)
      this.buffer = this.buffer.slice(end + 1)
      end = this.findSentenceEnd()
    }
  }

  /** 流结束时冲刷残余文本（最后一句往往没有句读点） */
  flush(): void {
    const rest = this.buffer.trim()
    if (rest) this.onSentence(rest)
    this.buffer = ''
  }

  private findSentenceEnd(): number {
    const match = /[。!?!；;\n]/.exec(this.buffer)
    return match ? match.index : -1
  }
}

/** 把 markdown/公式转成适合朗读的纯文本 */
export function spokenText(sentence: string): string {
  return sentence
    .replace(/\$\$[\s\S]+?\$\$/g, '，公式，')
    .replace(/\$[^\n$]+?\$/g, '公式')
    .replace(/```[\s\S]*?```/g, '，代码片段，')
    .replace(/[*`#>]/g, '')
    .trim()
}

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
    return new Promise((resolve) => {
      const audio = new Audio(`data:audio/mpeg;base64,${base64}`)
      this.currentAudio = audio
      audio.onended = () => resolve()
      audio.onerror = () => resolve()
      audio.play().catch(() => resolve()) // 自动播放被拦等原因，跳过不阻塞队列
    })
  }
}
