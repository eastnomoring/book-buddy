/**
 * iOS 微信 / Safari 的自动播放限制适配。
 * 这些浏览器要求音频必须在用户手势内播放，TTS 流式回答时自动 play() 会被
 * NotAllowedError 拦下。这里在首次点按时标记解锁，被拦的音频挂起等待，
 * 下一次点按的手势回调里补播（play 在手势内调用才有效）。
 *
 * 播放队列本身是串行的（TTSPlayer 逐句 pump），同一时刻最多一个音频等待，
 * 不会出现多段音频同时补播叠音。
 */

let unlocked = false
const waiters: Array<() => void> = []

if (typeof document !== 'undefined') {
  document.addEventListener(
    'pointerdown',
    () => {
      unlocked = true
      const pending = waiters.splice(0)
      pending.forEach((fn) => fn())
    },
    { capture: true },
  )
}

function whenGesture(): Promise<void> {
  if (unlocked) return Promise.resolve()
  return new Promise((resolve) => waiters.push(resolve))
}

/**
 * 播放一个 Audio 元素直到结束（或出错），被自动播放限制拦下时等用户手势补播。
 * resolve 时机：播放结束 / 播放失败（非限制类错误）——不会因未交互而永久挂起队列之外的状态。
 */
export function playAudioElement(audio: HTMLAudioElement): Promise<void> {
  return new Promise((resolve) => {
    let settled = false
    const settle = () => {
      if (!settled) {
        settled = true
        resolve()
      }
    }
    audio.addEventListener('ended', settle)
    audio.addEventListener('error', settle)

    audio.play().catch((err: unknown) => {
      if (err instanceof DOMException && err.name === 'NotAllowedError') {
        // 等用户下一次点按，在手势内补播；补播仍失败则放弃本段，不阻塞队列
        void whenGesture().then(() => audio.play().catch(settle))
      } else {
        settle()
      }
    })
  })
}
