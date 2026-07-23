"""数据模型初始化"""
from app.models.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    BookInfo,
    BookUploadResponse,
    BookSearchRequest,
    BookSearchResult,
    VoiceTranscribeRequest,
    VoiceTranscribeResponse,
    VoiceSynthesizeRequest,
    VoiceSynthesizeResponse,
)

__all__ = [
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "BookInfo",
    "BookUploadResponse",
    "BookSearchRequest",
    "BookSearchResult",
    "VoiceTranscribeRequest",
    "VoiceTranscribeResponse",
    "VoiceSynthesizeRequest",
    "VoiceSynthesizeResponse",
]