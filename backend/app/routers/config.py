"""配置路由：查看/更新/测试 LLM 配置"""
import asyncio

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.config import (
    ConfigResponse,
    ConfigTestRequest,
    ConfigTestResult,
    ConfigUpdate,
)
from app.services.config_store import apply_to_settings, mask_key, update_env_file

router = APIRouter()

VALID_PROVIDERS = {"openai", "qwen"}


def _current_key() -> str:
    if settings.llm_provider == "qwen":
        return settings.dashscope_api_key or ""
    return settings.openai_api_key or ""


def _current_model() -> str:
    if settings.llm_provider == "qwen":
        return settings.llm_model
    return settings.openai_model


def _current_base_url() -> str:
    if settings.llm_provider == "qwen":
        return ""
    return settings.openai_base_url


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """获取当前 LLM 配置（key 只返回掩码）"""
    key = _current_key()
    return ConfigResponse(
        provider=settings.llm_provider,
        base_url=_current_base_url(),
        model=_current_model(),
        api_key_masked=mask_key(key),
        configured=bool(key),
    )


@router.put("/config", response_model=ConfigResponse)
async def update_config(update: ConfigUpdate):
    """更新配置：写回 .env 并热生效；api_key 留空表示保留原 key"""
    provider = update.provider
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"不支持的提供商: {provider}")

    env_updates = {"LLM_PROVIDER": provider}
    if provider == "openai":
        if update.api_key:
            env_updates["OPENAI_API_KEY"] = update.api_key
        if update.base_url:
            env_updates["OPENAI_BASE_URL"] = update.base_url
        if update.model:
            env_updates["OPENAI_MODEL"] = update.model
    else:  # qwen
        if update.api_key:
            env_updates["DASHSCOPE_API_KEY"] = update.api_key
        if update.model:
            env_updates["LLM_MODEL"] = update.model

    try:
        update_env_file(env_updates)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"写入配置失败: {str(e)}") from e

    apply_to_settings(env_updates)
    return await get_config()


@router.post("/config/test", response_model=ConfigTestResult)
async def test_config(request: ConfigTestRequest):
    """用给定配置发一条最小调用测试连通性；api_key 留空则用已保存的 key"""
    provider = request.provider
    if provider not in VALID_PROVIDERS:
        return ConfigTestResult(ok=False, message=f"不支持的提供商: {provider}")

    try:
        if provider == "openai":
            from openai import AsyncOpenAI

            api_key = request.api_key or settings.openai_api_key
            if not api_key:
                return ConfigTestResult(ok=False, message="未提供 API Key")
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=request.base_url or settings.openai_base_url,
                timeout=15,
            )
            resp = await client.chat.completions.create(
                model=request.model or settings.openai_model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            reply = resp.choices[0].message.content or ""
            return ConfigTestResult(ok=True, message=f"连接成功（模型回复: {reply[:20] or 'OK'}）")

        # qwen
        import dashscope

        api_key = request.api_key or settings.dashscope_api_key
        if not api_key:
            return ConfigTestResult(ok=False, message="未提供 API Key")
        dashscope.api_key = api_key
        response = await asyncio.to_thread(
            dashscope.Generation.call,
            model=request.model or settings.llm_model,
            messages=[{"role": "user", "content": "hi"}],
        )
        if response.status_code == 200:
            return ConfigTestResult(ok=True, message="连接成功")
        return ConfigTestResult(ok=False, message=f"{response.code} - {response.message}")

    except Exception as e:
        return ConfigTestResult(ok=False, message=str(e)[:200])
