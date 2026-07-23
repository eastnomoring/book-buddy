"""应用配置管理"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # API Keys
    dashscope_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    
    # LLM 配置
    llm_provider: str = "qwen"  # qwen | deepseek
    llm_model: str = "qwen-vl-max"  # 多模态模型
    llm_timeout: int = 60
    
    # RAG 配置
    embedding_model: str = "text-embedding-v2"
    vector_db_path: str = "./data/chroma"
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # 语音配置
    asr_provider: str = "qwen"  # qwen | aliyun
    tts_provider: str = "qwen"
    tts_voice: str = "longxiaochun"  # 通义千问 TTS 音色
    
    # 应用配置
    app_name: str = "Book Buddy"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings