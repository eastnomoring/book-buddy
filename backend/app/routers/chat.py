"""对话路由"""
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.models.chat import (
    ChatRequest,
    ChatResponse,
)
from app.services.llm import get_llm_service, LLMService
from app.services.rag import rag_service, RAGService
from app.services.voice import get_asr_service, ASRService

router = APIRouter()


def get_rag_service() -> RAGService:
    return rag_service


def _build_system_prompt(context: str, detailed: bool = True) -> str:
    if detailed:
        prompt = (
            "你是一个友善、专业的学习伴侣，帮助用户理解书本知识。\n"
            "请用清晰、循序渐进的方式解答问题。\n"
            "如果提供了书籍上下文，请优先基于书中的定义和符号体系回答。\n"
            "如果用户问的是具体问题，请给出详细推导或解释。"
        )
    else:
        prompt = "你是学习伴侣，请用清晰的方式解答问题。"

    if context:
        prompt += f"\n\n相关书籍内容：\n{context}"
    return prompt


def _retrieve_rag(rag: RAGService, user_text: str, book_id: str | None):
    context = ""
    sources: list[str] = []
    page_refs: list[int] = []

    if not book_id:
        return context, sources, page_refs

    try:
        context = rag.retrieve_context(
            query=user_text or "当前书页内容",
            book_id=book_id,
            top_k=3,
        )
        sources_data = rag.get_sources(user_text or "当前书页内容", book_id, 3)
        sources = [s["content"][:200] for s in sources_data]
        page_refs = [s["page"] for s in sources_data]
    except Exception as e:
        print(f"RAG 检索失败: {e}")

    return context, sources, page_refs


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    llm: LLMService = Depends(get_llm_service),
    rag: RAGService = Depends(get_rag_service),
    asr: ASRService = Depends(get_asr_service),
):
    """
    对话接口

    支持文本、图像、语音输入，返回文本和可选的语音输出
    """
    user_text = request.text or ""

    if request.audio and not request.text:
        try:
            user_text = await asr.transcribe(request.audio)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}") from e

    if not user_text and not request.image:
        raise HTTPException(status_code=400, detail="需要提供文本、图像或语音输入")

    if request.page_number:
        page_hint = f"（用户当前在阅读第 {request.page_number} 页）"
        user_text = f"{page_hint}\n{user_text}" if user_text else page_hint

    context, sources, page_refs = _retrieve_rag(rag, user_text, request.book_id)
    system_prompt = _build_system_prompt(context, detailed=True)

    history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.history[-10:]
    ]

    try:
        full_prompt = f"{system_prompt}\n\n用户问题：{user_text or '请解释这张图片的内容'}"
        response_text = await llm.chat(
            text=full_prompt,
            image=request.image,
            history=history,
            stream=False,
        )
        if not isinstance(response_text, str):
            raise TypeError("非流式 LLM 应返回字符串")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {str(e)}") from e

    return ChatResponse(
        text=response_text,
        audio=None,
        sources=sources,
        page_references=page_refs,
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    llm: LLMService = Depends(get_llm_service),
    rag: RAGService = Depends(get_rag_service),
):
    """
    流式对话接口

    返回 SSE 流，适合实时显示长回复
    """
    user_text = request.text or ""

    if not user_text and not request.image:
        raise HTTPException(status_code=400, detail="需要提供文本或图像输入")

    if request.page_number:
        page_hint = f"（用户当前在阅读第 {request.page_number} 页）"
        user_text = f"{page_hint}\n{user_text}" if user_text else page_hint

    context, _, _ = _retrieve_rag(rag, user_text, request.book_id)
    system_prompt = _build_system_prompt(context, detailed=False)
    full_prompt = f"{system_prompt}\n\n用户问题：{user_text or '请解释这张图片的内容'}"

    history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.history[-10:]
    ]

    async def generate():
        try:
            stream = await llm.chat(
                text=full_prompt,
                image=request.image,
                history=history,
                stream=True,
            )

            async for chunk in stream:
                data = json.dumps({"delta": chunk, "done": False}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            yield f"data: {json.dumps({'delta': '', 'done': True}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
