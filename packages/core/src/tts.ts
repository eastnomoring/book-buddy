/** 把 markdown/公式转成适合朗读的纯文本 */
export function spokenText(sentence: string): string {
  return sentence
    .replace(/\$\$[\s\S]+?\$\$/g, '，公式，')
    .replace(/\$[^\n$]+?\$/g, '公式')
    .replace(/```[\s\S]*?```/g, '，代码片段，')
    .replace(/[*`#>]/g, '')
    .trim()
}

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
