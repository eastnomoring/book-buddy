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
from app.models.config import (
    ConfigResponse,
    ConfigUpdate,
    ConfigTestRequest,
    ConfigTestResult,
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