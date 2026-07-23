"""语音服务：ASR + TTS"""
import base64
import tempfile
import os
from typing import Optional
from abc import ABC, abstractmethod

from app.config import settings


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
    """通义千问语音识别"""
    
    def __init__(self):
        self.api_key = settings.dashscope_api_key
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 未设置")
    
    async def transcribe(self, audio_base64: str, format: str = "webm") -> str:
        """
        语音转文字
        
        Args:
            audio_base64: 音频 base64
            format: 音频格式
        
        Returns:
            转写文本
        """
        # TODO: 实现通义千问 Audio API 调用
        # 当前返回占位实现
        
        # 将 base64 解码为临时文件
        audio_bytes = base64.b64decode(audio_base64)
        
        # 占位返回
        return "[语音转写结果占位 - 实际需调用 Qwen-Audio API]"


class QwenTTSService(TTSService):
    """通义千问语音合成"""
    
    def __init__(self):
        self.api_key = settings.dashscope_api_key
        self.default_voice = settings.tts_voice
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 未设置")
    
    async def synthesize(self, text: str, voice: Optional[str] = None) -> str:
        """
        文字转语音
        
        Args:
            text: 要合成的文本
            voice: 音色（可选）
        
        Returns:
            音频 base64
        """
        # TODO: 实现通义千问 TTS API 调用
        # 当前返回占位实现
        
        import wave
        import io
        
        # 占位：生成一个简单的静音 WAV
        # 实际应调用 DashScope TTS API
        voice = voice or self.default_voice
        
        # 返回一个最小有效 WAV base64（静音）
        # 实际需要调用 API
        return "[TTS 音频 base64 占位]"


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