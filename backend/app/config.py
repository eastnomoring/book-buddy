"""应用配置管理"""
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
    
    # LLM 配置
    llm_provider: str = "qwen"  # qwen | deepseek | openai
    llm_model: str = "qwen-vl-max"  # 多模态模型
    llm_timeout: int = 60

    # OpenAI 兼容接口（智谱 / 硅基流动 / Ollama 通用）
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    openai_model: str = "glm-4.6v"
    # GLM-4.6V 的思考模式开关：讲解复杂证明时开启（走 reasoning_content），
    # 日常问答关闭以降低首字延迟。对应 API 的 extra_body.thinking.type
    openai_thinking: bool = False
    
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

    # MCP 代码执行（里程碑特性，默认关闭）
    mcp_code_enabled: bool = False

    # Anki 卡片生成（里程碑特性，默认关闭；需用户本地运行 Anki + AnkiConnect）
    anki_enabled: bool = False

    # 本地笔记沉淀（零依赖 markdown；默认开启，测试可关以免强制走 tool loop）
    notes_enabled: bool = True

    # 书籍上传大小上限（MB），超出返回 413
    max_upload_mb: int = 50


# 全局配置实例
settings = Settings()