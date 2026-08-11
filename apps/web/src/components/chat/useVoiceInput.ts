import { ref, type Ref } from 'vue'
import { transcribeVoice } from '../../api/client'
import { startRecording, type VoiceRecorder } from '../../utils/audio'

interface VoiceInputOptions {
  /** 后端已配 DashScope key → 服务端 ASR；否则浏览器 Web Speech 兜底 */
  voiceConfigured: Ref<boolean>
  onError: (message: string) => void
  /** Web Speech 边说边出字：实时回填输入框 */
  onInterim: (text: string) => void
  /** 识别出最终文本：填入输入框并发送 */
  onTranscribed: (text: string) => void | Promise<void>
}

export function useVoiceInput({ voiceConfigured, onError, onInterim, onTranscribed }: VoiceInputOptions) {
  const isRecording = ref(false)
  const isTranscribing = ref(false)
  let recorder: VoiceRecorder | null = null
  let recognition: { stop: () => void } | null = null

  /** 麦克风按钮：点一下开始录音，再点一下结束并转写发送 */
  async function toggleVoiceInput() {
    if (isRecording.value) {
      await stopVoiceInput()
      return
    }

    if (voiceConfigured.value) {
      // 服务端 ASR：WAV 录音 → /voice/transcribe
      try {
        recorder = await startRecording()
        isRecording.value = true
      } catch (e) {
        console.error(e)
        onError('无法访问麦克风，请检查浏览器权限')
      }
    } else {
      startWebSpeech()
    }
  }

  async function stopVoiceInput() {
    if (!voiceConfigured.value) {
      recognition?.stop() // onend 回调里处理发送
      return
    }

    const current = recorder
    recorder = null
    isRecording.value = false
    if (!current) return

    isTranscribing.value = true
    try {
      const wavBase64 = await current.stop()
      const result = await transcribeVoice(wavBase64, 'wav')
      const text = result.text.trim()
      if (text) {
        await onTranscribed(text)
      }
    } catch (e) {
      console.error(e)
      onError(e instanceof Error ? e.message : '语音识别失败，请重试')
    } finally {
      isTranscribing.value = false
    }
  }

  /** 浏览器 Web Speech 兜底：边说边出字，说完自动发送 */
  function startWebSpeech() {
    const w = window as unknown as Record<string, unknown>
    const SR = (w.SpeechRecognition || w.webkitSpeechRecognition) as (new () => {
      lang: string
      interimResults: boolean
      continuous: boolean
      onresult: (e: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void
      onend: () => void
      onerror: () => void
      start: () => void
      stop: () => void
    }) | undefined

    if (!SR) {
      onError('当前浏览器不支持语音识别，请在设置中配置语音 Key')
      return
    }

    const rec = new SR()
    let finalText = ''
    rec.lang = 'zh-CN'
    rec.interimResults = true
    rec.continuous = false
    rec.onresult = (e) => {
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript
        if (e.results[i].isFinal) finalText += t
        else interim += t
      }
      onInterim(finalText + interim)
    }
    rec.onend = () => {
      isRecording.value = false
      recognition = null
      if (finalText.trim()) {
        void onTranscribed(finalText.trim())
      }
    }
    rec.onerror = () => {
      isRecording.value = false
      recognition = null
      onError('语音识别失败，请重试')
    }

    recognition = rec
    isRecording.value = true
    rec.start()
  }

  function cancel() {
    recorder?.cancel()
    recognition?.stop()
  }

  return { isRecording, isTranscribing, toggleVoiceInput, cancel }
}
