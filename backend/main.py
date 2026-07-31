"""
Book Buddy Backend
AI 伴读系统后端服务
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🚀 Book Buddy Backend 启动...")
    # 启动时从磁盘重建书籍索引（PDF 与向量数据已持久化）
    try:
        from app.routers.book import rebuild_books_index
        n = rebuild_books_index()
        if n:
            print(f"📖 已恢复 {n} 本书的索引")
    except Exception as e:
        print(f"⚠️ 恢复书籍索引失败: {e}")
    yield
    # 关闭时：清理资源
    print("👋 Book Buddy Backend 关闭")

app = FastAPI(
    title="Book Buddy API",
    description="AI 伴读系统后端",
    version="0.1.0",
    lifespan=lifespan,
)

from app.config import settings

# CORS 配置（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "message": "Book Buddy API 运行中"}

@app.get("/health")
async def health():
    """详细健康检查"""
    return {
        "status": "healthy",
        "llm": f"{settings.llm_provider}:{settings.openai_model if settings.llm_provider == 'openai' else settings.llm_model}",
        "rag": "ready",
    }

# 注册路由
from app.routers import chat, voice, book, config

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(voice.router, prefix="/api", tags=["voice"])
app.include_router(book.router, prefix="/api", tags=["books"])
app.include_router(config.router, prefix="/api", tags=["config"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )