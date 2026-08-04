/**
 * 平台适配接口定义（纯类型，零实现，零 DOM/wx 引用）。
 *
 * 各端（apps/web、apps/mp、apps/desktop）各自实现这些接口，
 * 组件层只面向接口编程，实现跨端复用。
 *
 * 接口冻结于 2026-08-03（见 docs/TASK_SPLIT_MULTI_PLATFORM.md §5）。
 * 改签名前必须在协调记录说明影响面。
 */
import type { ChatRequest } from './types.js'

/**
 * 统一错误类型。各端 adapter 用它包装平台原生错误（wx.fail / DOMException 等），
 * 避免上层组件被各端错误形状绑架。
 */
export class PlatformError extends Error {
  /** 原始平台错误，便于调试；不保证结构 */
  readonly cause?: unknown

  constructor(message: string, cause?: unknown) {
    super(message)
    this.name = 'PlatformError'
    this.cause = cause
  }
}

/** 拍照/选图产物：裸 base64（无 data: 前缀）+ 媒体类型 */
export interface PhotoResult {
  /** 裸 base64，不含 `data:image/...;base64,` 前缀 */
  base64: string
  /** 形如 `image/jpeg`；后端 /api/chat image 字段收裸 base64 */
  mediaType: string
}

/** 录音产物：裸 base64 + mimeType + 采样率（ASR 需要） */
export interface AudioRecordResult {
  /** 裸 base64，不含 `data:audio/...;base64,` 前缀 */
  base64: string
  /** 形如 `audio/wav`、`audio/mpeg`；后端 /api/voice/transcribe audio 收裸 base64 */
  mimeType: string
  /** 采样率（Hz），Web 端固定 16000；小程序端由 RecorderManager 决定 */
  sampleRate: number
}

/** 流式对话回调。任一 onChunk/onDone/onError 触发后，后续不再回调 */
export interface ChatStreamCallbacks {
  /** 每收到一个 delta 文本触发 */
  onChunk: (delta: string) => void
  /** 正常结束触发；与 onError 互斥 */
  onDone: () => void
  /** 出错触发；与 onDone 互斥 */
  onError: (err: PlatformError) => void
}

/** chatStream 返回的控制句柄，用于提前中止请求 */
export interface ChatStreamHandle {
  /** 中止请求；中止后不再触发任何回调 */
  abort: () => void
}

/**
 * 流式对话能力。
 * 实现端复用 core 的 SSEParser / buildChatBody / API_PATHS，
 * 只负责「传输层」（fetch / wx.request / Tauri invoke）。
 */
export interface ChatTransport {
  /**
   * 发起流式对话。
   * @param req 对话请求（文本/图片/历史等）
   * @param cb 流式回调
   * @returns 控制句柄，用于 abort
   */
  chatStream(req: ChatRequest, cb: ChatStreamCallbacks): ChatStreamHandle
}

/** 拍照/选图能力 */
export interface PhotoCapture {
  /**
   * 调起相机拍照或从相册选图（由实现端决定具体交互）。
   * @returns 图片产物；用户取消时应 reject 为 PlatformError
   */
  capture(): Promise<PhotoResult>
}

/**
 * 录音能力：start 后到 stop 之间采集。
 * 最大录音时长等健壮性保护属实现端职责，不进接口签名。
 */
export interface AudioRecorder {
  /** 开始录音；权限不足/设备不可用时 reject 为 PlatformError */
  start(): Promise<void>
  /** 结束录音并返回产物 */
  stop(): Promise<AudioRecordResult>
  /** 放弃录音（不产出音频，立即释放资源） */
  cancel(): void
}

/**
 * TTS 播放能力。
 * @param base64 裸 base64 音频
 * @param mimeType 形如 `audio/mpeg`
 * 长句是否落临时文件由实现端决定（如小程序 InnerAudioContext 对超长 data URI 不稳）。
 */
export interface AudioPlayer {
  /** 播放；resolve 于自然播完，reject 于出错 */
  play(base64: string, mimeType: string): Promise<void>
  /** 立即停止当前播放 */
  stop(): void
}
