/**
 * 录音输入：16kHz 单声道 WAV → 后端 ASR 转写 → 回填输入框。
 */
import { ref, type Ref } from 'vue'
import { MpAudioRecorder } from '../../platform/audioRecorder'
import { transcribeVoice } from '../../platform/voice'

export function useVoiceInput(options: {
  inputText: Ref<string>
  error: Ref<string>
}) {
  const { inputText, error } = options
  const recorder = new MpAudioRecorder()
  const isRecording = ref(false)
  const isTranscribing = ref(false)

  async function toggleRecord() {
    if (isRecording.value) {
      isRecording.value = false
      isTranscribing.value = true
      try {
        const result = await recorder.stop()
        const transcription = await transcribeVoice(
          result.base64,
          result.mimeType.split('/')[1],
        )
        const text = transcription.text.trim()
        if (text) {
          inputText.value = text
        }
      } catch (e) {
        error.value = e instanceof Error ? e.message : '语音识别失败'
      } finally {
        isTranscribing.value = false
      }
    } else {
      error.value = ''
      try {
        await recorder.start()
        isRecording.value = true
      } catch (e) {
        error.value = e instanceof Error ? e.message : '无法启动录音'
      }
    }
  }

  return { isRecording, isTranscribing, toggleRecord }
}
