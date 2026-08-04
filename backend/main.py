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

    # 代码执行：仅配置开启时暴露给 LLM（模块内已预注册，此处仅日志）
    if settings.mcp_code_enabled:
        from app.mcp.registry import register_code_tool
        register_code_tool()
        print("🧪 代码执行工具已启用（MCP_CODE_ENABLED=true）")

    # 条件注册 Anki 工具（ANKI_ENABLED=true 时）
    if settings.anki_enabled:
        try:
            from app.mcp.anki import register_anki_tool, AnkiConnectClient
            if AnkiConnectClient().ping():
                register_anki_tool()
                print("📇 Anki 工具已注册（AnkiConnect 可用）")
            else:
                print("⚠️ ANKI_ENABLED=true 但 AnkiConnect 不可用，工具未注册（请检查 Anki 是否运行）")
        except Exception as e:
            print(f"⚠️ Anki 工具注册失败: {e}")

    # 笔记工具（NOTES_ENABLED，默认开；零依赖本地 markdown）
    if settings.notes_enabled:
        try:
            from app.mcp.notes import register_note_tool
            register_note_tool()
            print("📝 笔记工具已注册")
        except Exception as e:
            print(f"⚠️ 笔记工具注册失败: {e}")

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
from app.middleware.auth import auth_middleware

# CORS 配置（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Token 鉴权（AUTH_TOKEN 环境变量设置时启用，默认关闭）
app.middleware("http")(auth_middleware)

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
from app.routers import chat, voice, book, config, formula

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(voice.router, prefix="/api", tags=["voice"])
app.include_router(book.router, prefix="/api", tags=["books"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(formula.router, prefix="/api", tags=["formula"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )