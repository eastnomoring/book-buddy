"""对话路由"""
import json
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ChatStreamChunk,
    ChatMessage,
)
from app.services.llm import get_llm_service, LLMService
from app.services.rag import rag_service, RAGService
from app.services.voice import get_asr_service, get_tts_service, ASRService, TTSService

router = APIRouter()


def get_rag_service() -> RAGService:
    return rag_service


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    llm: LLMService = Depends(get_llm_service),
    rag: RAGService = Depends(get_rag_service),
    asr: ASRService = Depends(get_asr_service),
    tts: TTSService = Depends(get_tts_service),
):
    """
    对话接口
    
    支持文本、图像、语音输入，返回文本和可选的语音输出
    """
    # 1. 处理输入
    user_text = request.text or ""
    
    # 如果有语音输入，先转写
    if request.audio and not request.text:
        try:
            user_text = await asr.transcribe(request.audio)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")
    
    if not user_text and not request.image:
        raise HTTPException(status_code=400, detail="需要提供文本、图像或语音输入")
    
    # 2. RAG 检索相关上下文
    context = ""
    sources = []
    page_refs = []
    
    if request.book_id:
        try:
            context = rag.retrieve_context(
                query=user_text,
                book_id=request.book_id,
                top_k=3,
            )
            sources_data = rag.get_sources(user_text, request.book_id, 3)
            sources = [s["content"][:200] for s in sources_data]
            page_refs = [s["page"] for s in sources_data]
        except Exception as e:
            # RAG 失败不影响主流程
            print(f"RAG 检索失败: {e}")
    
    # 3. 构建提示词
    system_prompt = """你是一个友善、专业的学习伴侣，帮助用户理解书本知识。
请用清晰、循序渐进的方式解答问题。
如果提供了书籍上下文，请优先基于书中的定义和符号体系回答。
如果用户问的是具体问题，请给出详细推导或解释。"""

    if context:
        system_prompt += f"\n\n相关书籍内容：\n{context}"
    
    # 4. 构建对话历史
    history = []
    for msg in request.history[-10:]:  # 最多保留 10 轮
        history.append({
            "role": msg.role,
            "content": msg.content,
        })
    
    # 5. 调用 LLM
    try:
        # 合并系统提示和用户输入
        full_prompt = f"{system_prompt}\n\n用户问题：{user_text}"
        
        response_text = await run_in_threadpool(
            lambda: llm.chat(text=full_prompt, image=request.image, history=history, stream=False)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {str(e)}")
    
    # 6. 可选：生成语音回复
    audio_response = None
    # 暂时跳过语音生成，后续实现流式 TTS
    # if response_text:
    #     try:
    #         audio_response = await tts.synthesize(response_text)
    #     except Exception as e:
    #         print(f"TTS 失败: {e}")
    
    return ChatResponse(
        text=response_text,
        audio=audio_response,
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
    # 处理输入（同上）
    user_text = request.text or ""
    
    if not user_text and not request.image:
        raise HTTPException(status_code=400, detail="需要提供文本或图像输入")
    
    # RAG 检索
    context = ""
    if request.book_id:
        try:
            context = rag.retrieve_context(user_text, request.book_id, 3)
        except Exception as e:
            print(f"RAG 失败: {e}")
    
    # 构建提示词
    system_prompt = "你是学习伴侣，请用清晰的方式解答问题。"
    if context:
        system_prompt += f"\n\n相关内容：\n{context}"
    
    full_prompt = f"{system_prompt}\n\n用户问题：{user_text}"
    
    # 流式生成
    async def generate():
        try:
            stream = llm.chat(
                text=full_prompt,
                image=request.image,
                stream=True,
            )
            
            full_content = ""
            for chunk in stream:
                full_content += chunk
                data = json.dumps({"delta": chunk, "done": False})
                yield f"data: {data}\n\n"
            
            # 结束标记
            yield f"data: {json.dumps({'delta': '', 'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )