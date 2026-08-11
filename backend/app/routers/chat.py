"""对话路由"""
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models.chat import (
    ChatRequest,
    ChatResponse,
)
from app.services.llm import LLMService, get_llm_service
from app.services.page_locator import locate_page
from app.services.rag import RAGService, rag_service
from app.services.voice import ASRService, get_asr_service

logger = logging.getLogger(__name__)

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


def _retrieve_rag(
    rag: RAGService,
    user_text: str,
    book_id: str | None,
    chapter: str | None = None,
    near_page: int | None = None,
):
    """同步检索（可被 to_thread 调用）。chapter/near_page 用于当前页定位收窄。"""
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
            chapter=chapter,
            near_page=near_page,
        )
        sources_data = rag.get_sources(
            user_text or "当前书页内容", book_id, 3,
            chapter=chapter, near_page=near_page,
        )
        sources = [s["content"][:200] for s in sources_data]
        page_refs = [s["page"] for s in sources_data]
    except Exception as e:
        logger.warning("RAG 检索失败: %s", e)

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

    retrieval_text = user_text  # 检索用原始问题，不混入页码提示

    # 当前页定位：有图时先识别页码/章节，收窄 RAG（失败降级为整书 RAG）
    located_chapter = None
    located_page = None
    if request.image and request.book_id:
        located = await locate_page(llm, request.image, request.media_type)
        located_chapter = located.get("chapter")
        located_page = located.get("page")

    if request.page_number:
        page_hint = f"（用户当前在阅读第 {request.page_number} 页）"
        user_text = f"{page_hint}\n{user_text}" if user_text else page_hint
    elif located_page:
        # 识别到页码时告知 LLM，营造「它知道你在读哪页」的体验
        loc_hint = f"（看起来你在读第 {located_page} 页"
        if located_chapter:
            loc_hint += f" / {located_chapter}"
        loc_hint += "）"
        user_text = f"{loc_hint}\n{user_text}" if user_text else loc_hint

    context, sources, page_refs = await asyncio.to_thread(
        _retrieve_rag, rag, retrieval_text, request.book_id,
        located_chapter, located_page,
    )
    system_prompt = _build_system_prompt(context, detailed=True)

    history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.history[-10:]
    ]

    try:
        full_prompt = f"{system_prompt}\n\n用户问题：{user_text or '请解释这张图片的内容'}"

        # 任一活跃 MCP 工具（代码执行 / Anki / 笔记）且 LLM 支持工具调用时走 tool loop
        from app.mcp.registry import should_use_tool_loop
        if should_use_tool_loop(llm):
            from app.mcp.tool_loop import run_chat_with_tools
            response_text = await run_chat_with_tools(
                llm=llm,
                system_prompt=system_prompt,
                user_text=user_text or "请解释这张图片的内容",
                history=history,
                image=request.image,
                media_type=request.media_type,
            )
        else:
            response_text = await llm.chat(
                text=full_prompt,
                image=request.image,
                history=history,
                stream=False,
                media_type=request.media_type,
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

    retrieval_text = user_text  # 检索用原始问题，不混入页码提示

    # 当前页定位（同非流式）
    located_chapter = None
    located_page = None
    if request.image and request.book_id:
        located = await locate_page(llm, request.image, request.media_type)
        located_chapter = located.get("chapter")
        located_page = located.get("page")

    if request.page_number:
        page_hint = f"（用户当前在阅读第 {request.page_number} 页）"
        user_text = f"{page_hint}\n{user_text}" if user_text else page_hint
    elif located_page:
        loc_hint = f"（看起来你在读第 {located_page} 页"
        if located_chapter:
            loc_hint += f" / {located_chapter}"
        loc_hint += "）"
        user_text = f"{loc_hint}\n{user_text}" if user_text else loc_hint

    context, _, _ = await asyncio.to_thread(
        _retrieve_rag, rag, retrieval_text, request.book_id,
        located_chapter, located_page,
    )
    system_prompt = _build_system_prompt(context, detailed=False)
    full_prompt = f"{system_prompt}\n\n用户问题：{user_text or '请解释这张图片的内容'}"

    history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.history[-10:]
    ]

    async def _plain_text_events():
        """无 tool loop 时的纯文本事件流"""
        stream = await llm.chat(
            text=full_prompt,
            image=request.image,
            history=history,
            stream=True,
            media_type=request.media_type,
        )
        async for chunk in stream:
            yield {"delta": chunk, "done": False}
        yield {"delta": "", "done": True}

    async def generate():
        try:
            from app.mcp.registry import should_use_tool_loop
            from app.services.stream_tts import iter_with_sentence_tts

            # Z4：可选服务端按句 TTS（需 DashScope key）
            tts = None
            if request.enable_tts and settings.dashscope_api_key:
                try:
                    from app.services.voice import get_tts_service
                    tts = get_tts_service()
                except Exception as e:
                    logger.warning("⚠️ enable_tts 但 TTS 不可用，降级为纯文本流: %s", e)

            if should_use_tool_loop(llm):
                from app.mcp.tool_loop import run_chat_with_tools_stream
                upstream = run_chat_with_tools_stream(
                    llm=llm,
                    system_prompt=system_prompt,
                    user_text=user_text or "请解释这张图片的内容",
                    history=history,
                    image=request.image,
                    media_type=request.media_type,
                )
            else:
                upstream = _plain_text_events()

            async for event in iter_with_sentence_tts(upstream, tts):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
