"""S1: DeepSeekService 移除后的 get_llm_service 行为测试。"""
import pytest

from app.config import settings
from app.services.llm import get_llm_service, LLMService


def test_deepseek_provider_raises_clear_error(monkeypatch):
    """provider=deepseek 报明确错误，引导用户走 openai 兼容接口"""
    monkeypatch.setattr(settings, "llm_provider", "deepseek")
    with pytest.raises(ValueError, match="DeepSeek 请用 openai 兼容接口"):
        get_llm_service()


def test_unknown_provider_raises(monkeypatch):
    """未知 provider 报错"""
    monkeypatch.setattr(settings, "llm_provider", "claude")
    with pytest.raises(ValueError, match="不支持的 LLM 提供商"):
        get_llm_service()


def test_qwen_provider_still_works(monkeypatch):
    """qwen 路径不受影响"""
    monkeypatch.setattr(settings, "llm_provider", "qwen")
    monkeypatch.setattr(settings, "dashscope_api_key", "test-key")
    service = get_llm_service()
    assert isinstance(service, LLMService)


def test_openai_provider_still_works(monkeypatch):
    """openai 路径不受影响"""
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    service = get_llm_service()
    assert isinstance(service, LLMService)
