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
    # 启动时：初始化向量库、MCP 连接等
    print("🚀 Book Buddy Backend 启动...")
    yield
    # 关闭时：清理资源
    print("👋 Book Buddy Backend 关闭")

app = FastAPI(
    title="Book Buddy API",
    description="AI 伴读系统后端",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
        "llm": "qwen-vl",  # TODO: 实际检查连接
        "rag": "ready",
    }

# 注册路由
from app.routers import chat, voice, book

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(voice.router, prefix="/api", tags=["voice"])
app.include_router(book.router, tags=["books"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )