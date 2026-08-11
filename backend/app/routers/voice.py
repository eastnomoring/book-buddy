"""语音处理路由"""
import time

from fastapi import APIRouter, Depends, HTTPException

from app.models.chat import (
    VoiceSynthesizeRequest,
    VoiceSynthesizeResponse,
    VoiceTranscribeRequest,
    VoiceTranscribeResponse,
)
from app.services.voice import ASRService, TTSService, get_asr_service, get_tts_service

router = APIRouter()


@router.post("/voice/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_voice(
    request: VoiceTranscribeRequest,
    asr: ASRService = Depends(get_asr_service),
):
    """
    语音转文字

    接收音频 base64，返回转写文本
    """
    try:
        t0 = time.perf_counter()
        text = await asr.transcribe(request.audio, request.format)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        import base64
        audio_bytes = base64.b64decode(request.audio)
        # 假设 16kHz, 16bit, mono: 每秒 32000 字节
        duration = len(audio_bytes) / 32000

        return VoiceTranscribeResponse(
            text=text,
            duration=round(duration, 2),
            elapsed_ms=round(elapsed_ms, 1),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}") from e


@router.post("/voice/synthesize", response_model=VoiceSynthesizeResponse)
async def synthesize_voice(
    request: VoiceSynthesizeRequest,
    tts: TTSService = Depends(get_tts_service),
):
    """
    文字转语音

    接收文本，返回音频 base64
    """
    try:
        t0 = time.perf_counter()
        audio = await tts.synthesize(request.text, request.voice)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # 中文约 3-4 字符/秒
        duration = len(request.text) / 3.5

        return VoiceSynthesizeResponse(
            audio=audio,
            duration=round(duration, 2),
            elapsed_ms=round(elapsed_ms, 1),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}") from e
