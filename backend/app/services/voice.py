"""语音服务：ASR + TTS"""
import asyncio
import base64
import os
import tempfile
from typing import Optional
from abc import ABC, abstractmethod

from app.config import settings
from app.services.llm import extract_text_content


class ASRService(ABC):
    """语音识别抽象基类"""
    
    @abstractmethod
    async def transcribe(self, audio_base64: str, format: str = "webm") -> str:
        """语音转文字"""
        pass


class TTSService(ABC):
    """语音合成抽象基类"""
    
    @abstractmethod
    async def synthesize(self, text: str, voice: Optional[str] = None) -> str:
        """文字转语音，返回音频 base64"""
        pass


class QwenASRService(ASRService):
    """DashScope 语音识别（qwen3-asr-flash 系模型，走 MultiModalConversation）"""

    def __init__(self):
        if not settings.dashscope_api_key:
            raise ValueError("DASHSCOPE_API_KEY 未设置")

    async def transcribe(self, audio_base64: str, format: str = "wav") -> str:
        """
        语音转文字

        Args:
            audio_base64: 音频 base64（前端固定送 16kHz 单声道 WAV）
            format: 音频格式，仅用于临时文件扩展名

        Returns:
            转写文本
        """
        audio_bytes = base64.b64decode(audio_base64)
        if not audio_bytes:
            raise ValueError("音频内容为空")

        # DashScope 多模态接口以 file:// 本地路径接收音频，先落临时文件
        fd, tmp_path = tempfile.mkstemp(suffix=f".{format}")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(audio_bytes)
            return await asyncio.to_thread(self._call_asr, tmp_path)
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def _call_asr(self, audio_path: str) -> str:
        import dashscope
        from dashscope import MultiModalConversation

        # 每次调用重新读 key，配合设置面板热更新
        dashscope.api_key = settings.dashscope_api_key
        response = MultiModalConversation.call(
            model=settings.asr_model,
            messages=[{
                "role": "user",
                "content": [
                    {"audio": f"file://{audio_path}"},
                    {"text": ""},
                ],
            }],
        )
        if response.status_code != 200:
            raise RuntimeError(f"ASR 错误: {response.code} - {response.message}")

        text = extract_text_content(response.output.choices[0].message.content).strip()
        if not text:
            raise RuntimeError("未识别到语音内容")
        return text


class QwenTTSService(TTSService):
    """DashScope 语音合成（cosyvoice 系模型）"""

    def __init__(self):
        if not settings.dashscope_api_key:
            raise ValueError("DASHSCOPE_API_KEY 未设置")

    async def synthesize(self, text: str, voice: Optional[str] = None) -> str:
        """
        文字转语音

        Args:
            text: 要合成的文本（前端按句调用）
            voice: 音色（可选，默认 settings.tts_voice）

        Returns:
            音频 base64（mp3）
        """
        text = text.strip()
        if not text:
            raise ValueError("合成文本为空")
        return await asyncio.to_thread(self._call_tts, text, voice or settings.tts_voice)

    def _call_tts(self, text: str, voice: str) -> str:
        import dashscope
        from dashscope.audio.tts_v2 import SpeechSynthesizer

        dashscope.api_key = settings.dashscope_api_key
        synthesizer = SpeechSynthesizer(model=settings.tts_model, voice=voice)
        audio_bytes = synthesizer.call(text)
        if not isinstance(audio_bytes, (bytes, bytearray)) or not audio_bytes:
            resp = synthesizer.get_response()
            raise RuntimeError(f"TTS 错误: {resp}")
        return base64.b64encode(bytes(audio_bytes)).decode("ascii")


class AliyunASRService(ASRService):
    """阿里云语音识别（备选）"""
    
    async def transcribe(self, audio_base64: str, format: str = "webm") -> str:
        """TODO: 实现阿里云 ASR"""
        raise NotImplementedError("阿里云 ASR 待实现")


class AliyunTTSService(TTSService):
    """阿里云语音合成（备选）"""
    
    async def synthesize(self, text: str, voice: Optional[str] = None) -> str:
        """TODO: 实现阿里云 TTS"""
        raise NotImplementedError("阿里云 TTS 待实现")


def get_asr_service() -> ASRService:
    """获取 ASR 服务实例"""
    provider = settings.asr_provider
    
    if provider == "qwen":
        return QwenASRService()
    elif provider == "aliyun":
        return AliyunASRService()
    else:
        raise ValueError(f"不支持的 ASR 提供商: {provider}")


def get_tts_service() -> TTSService:
    """获取 TTS 服务实例"""
    provider = settings.tts_provider
    
    if provider == "qwen":
        return QwenTTSService()
    elif provider == "aliyun":
        return AliyunTTSService()
    else:
        raise ValueError(f"不支持的 TTS 提供商: {provider}")