"""Pydantic 数据模型"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# ============ Chat 模型 ============

class ChatMessage(BaseModel):
    """单条对话消息"""
    role: str = Field(..., description="角色: user | assistant")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """对话请求"""
    text: Optional[str] = Field(None, description="文本输入")
    image: Optional[str] = Field(None, description="图像 base64")
    media_type: Optional[str] = Field(None, description="图片媒体类型，如 image/jpeg、image/png；缺省回退 image/jpeg")
    audio: Optional[str] = Field(None, description="音频 base64")
    book_id: Optional[str] = Field(None, description="当前书籍 ID")
    page_number: Optional[int] = Field(None, description="当前页码")
    history: List[ChatMessage] = Field(default_factory=list, description="对话历史")
    enable_tts: bool = Field(
        False,
        description="Z4：流式对话时由服务端按句合成 TTS，经 type=audio 事件下发（省去前端每句 HTTP）",
    )


class ChatResponse(BaseModel):
    """对话响应"""
    text: str = Field(..., description="回复文本")
    audio: Optional[str] = Field(None, description="回复音频 base64（流式时为 None）")
    sources: List[str] = Field(default_factory=list, description="引用的书籍段落")
    page_references: List[int] = Field(default_factory=list, description="引用的页码")


# ============ Book 模型 ============

class BookInfo(BaseModel):
    """书籍信息"""
    id: str = Field(..., description="书籍 ID")
    title: str = Field(..., description="书名")
    author: Optional[str] = Field(None, description="作者")
    total_pages: int = Field(..., description="总页数")
    chapters: List[dict] = Field(default_factory=list, description="章节列表")
    created_at: datetime = Field(default_factory=datetime.now)


class BookUploadResponse(BaseModel):
    """书籍上传响应"""
    id: str
    title: str
    message: str = "书籍上传成功，正在解析..."


class BookSearchRequest(BaseModel):
    """书籍检索请求"""
    query: str = Field(..., description="检索查询")
    book_id: Optional[str] = Field(None, description="限定书籍")
    top_k: int = Field(5, description="返回结果数量")


class BookSearchResult(BaseModel):
    """书籍检索结果"""
    content: str
    page: int
    chapter: Optional[str]
    score: float


# ============ Voice 模型 ============

class VoiceTranscribeRequest(BaseModel):
    """语音转写请求"""
    audio: str = Field(..., description="音频 base64")
    format: str = Field("webm", description="音频格式: webm | wav | mp3")


class VoiceTranscribeResponse(BaseModel):
    """语音转写响应"""
    text: str
    duration: float  # 秒
    elapsed_ms: float = Field(0, description="服务端处理耗时（毫秒），用于延迟观测")


class VoiceSynthesizeRequest(BaseModel):
    """语音合成请求"""
    text: str
    voice: Optional[str] = None


class VoiceSynthesizeResponse(BaseModel):
    """语音合成响应"""
    audio: str  # base64
    duration: float
    elapsed_ms: float = Field(0, description="服务端处理耗时（毫秒），用于延迟观测")