"""配置相关 Pydantic 模型"""
from typing import Optional
from pydantic import BaseModel, Field


class ConfigResponse(BaseModel):
    """当前 LLM 配置（key 只返回掩码）"""
    provider: str
    base_url: Optional[str] = None
    model: str
    api_key_masked: str = ""
    configured: bool = False


class ConfigUpdate(BaseModel):
    """更新配置；api_key 留空表示保留原 key"""
    provider: str = Field(..., description="openai | qwen")
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class ConfigTestRequest(BaseModel):
    """测试连接；api_key 留空则用已保存的 key"""
    provider: str = Field(..., description="openai | qwen")
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class ConfigTestResult(BaseModel):
    ok: bool
    message: str
