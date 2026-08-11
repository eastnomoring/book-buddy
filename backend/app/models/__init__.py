"""数据模型初始化"""
from app.models.chat import (
    BookInfo,
    BookSearchRequest,
    BookSearchResult,
    BookUploadResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    VoiceSynthesizeRequest,
    VoiceSynthesizeResponse,
    VoiceTranscribeRequest,
    VoiceTranscribeResponse,
)
from app.models.config import (
    ConfigResponse,
    ConfigTestRequest,
    ConfigTestResult,
    ConfigUpdate,
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
    "ConfigResponse",
    "ConfigUpdate",
    "ConfigTestRequest",
    "ConfigTestResult",
]