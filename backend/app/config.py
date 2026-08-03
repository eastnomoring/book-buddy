"""应用配置管理"""
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # API Keys
    dashscope_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    
    # LLM 配置
    llm_provider: str = "qwen"  # qwen | deepseek | openai
    llm_model: str = "qwen-vl-max"  # 多模态模型
    llm_timeout: int = 60

    # OpenAI 兼容接口（智谱 / 硅基流动 / Ollama 通用）
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    openai_model: str = "glm-4v-flash"
    
    # RAG 配置
    embedding_provider: str = "openai"  # openai（云端 API，中文效果好）| local（Chroma 默认模型）
    embedding_model: str = "embedding-3"
    vector_db_path: str = "./data/chroma"
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # 语音配置
    asr_provider: str = "qwen"  # qwen | aliyun
    asr_model: str = "qwen3-asr-flash"  # DashScope 语音识别模型
    tts_provider: str = "qwen"
    tts_model: str = "cosyvoice-v2"  # DashScope 语音合成模型
    tts_voice: str = "longxiaochun_v2"  # cosyvoice-v2 音色
    
    # 应用配置
    app_name: str = "Book Buddy"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings