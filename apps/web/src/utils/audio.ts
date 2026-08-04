/**
 * WAV 录音器：getUserMedia + Web Audio 采集 PCM，重采样到 16kHz 单声道，
 * 编码为标准 WAV 后输出 base64。
 *
 * 不用 MediaRecorder 的 webm/opus，是为了让后端 ASR（DashScope）拿到
 * 兼容性最稳的 WAV 格式。
 */

export interface VoiceRecorder {
  /** 结束录音，返回 WAV base64 */
  stop: () => Promise<string>
  /** 放弃录音（不产出音频） */
  cancel: () => void
}

const TARGET_SAMPLE_RATE = 16000

/** 开始录音；用户拒绝授权或设备不可用时抛错 */
export async function startRecording(): Promise<VoiceRecorder> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  })

  const audioCtx = new AudioContext()
  const source = audioCtx.createMediaStreamSource(stream)
  // ScriptProcessor 已废弃但兼容性最好；录音时长短，性能无虞
  const processor = audioCtx.createScriptProcessor(4096, 1, 1)

  const chunks: Float32Array[] = []
  processor.onaudioprocess = (e) => {
    chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)))
  }

  source.connect(processor)
  processor.connect(audioCtx.destination) // ScriptProcessor 必须挂到输出才工作

  let finished = false
  const release = () => {
    finished = true
    processor.onaudioprocess = null
    source.disconnect()
    processor.disconnect()
    stream.getTracks().forEach((t) => t.stop())
    void audioCtx.close()
  }

  return {
    stop: () => {
      if (finished) return Promise.reject(new Error('录音已结束'))
      const recorded = chunks
      const sampleRate = audioCtx.sampleRate // close 前先取出来
      release()
      if (!recorded.length) return Promise.reject(new Error('没有录到声音'))
      const pcm = mergeChunks(recorded)
      const resampled = resample(pcm, sampleRate, TARGET_SAMPLE_RATE)
      const wav = encodeWav(resampled, TARGET_SAMPLE_RATE)
      return Promise.resolve(arrayBufferToBase64(wav))
    },
    cancel: () => {
      if (!finished) release()
    },
  }
}

function mergeChunks(chunks: Float32Array[]): Float32Array {
  const total = chunks.reduce((n, c) => n + c.length, 0)
  const out = new Float32Array(total)
  let offset = 0
  for (const c of chunks) {
    out.set(c, offset)
    offset += c.length
  }
  return out
}

/** 线性插值重采样（16kHz 语音足够） */
function resample(input: Float32Array, fromRate: number, toRate: number): Float32Array {
  if (fromRate === toRate) return input
  const ratio = fromRate / toRate
  const outLength = Math.round(input.length / ratio)
  const out = new Float32Array(outLength)
  for (let i = 0; i < outLength; i++) {
    const pos = i * ratio
    const idx = Math.floor(pos)
    const frac = pos - idx
    const a = input[idx] ?? 0
    const b = input[idx + 1] ?? a
    out[i] = a + (b - a) * frac
  }
  return out
}

/** 16-bit PCM WAV 编码 */
function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const dataLength = samples.length * 2
  const buffer = new ArrayBuffer(44 + dataLength)
  const view = new DataView(buffer)

  const writeString = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i))
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + dataLength, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true) // PCM chunk size
  view.setUint16(20, 1, true) // PCM format
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // byte rate
  view.setUint16(32, 2, true) // block align
  view.setUint16(34, 16, true) // bits per sample
  writeString(36, 'data')
  view.setUint32(40, dataLength, true)

  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    offset += 2
  }
  return buffer
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  const CHUNK = 0x8000
  for (let i = 0; i < bytes.length; i += CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(i, i + CHUNK))
  }
  return btoa(binary)
}
