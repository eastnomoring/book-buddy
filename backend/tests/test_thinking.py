"""R1: OpenAICompatibleService 的 thinking 模式开关测试。

不发起真实网络请求，只验证 extra_body 组装是否正确。
"""
import asyncio

import pytest

from app.config import settings
from app.services.llm import OpenAICompatibleService


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    return OpenAICompatibleService()


def test_thinking_body_disabled_by_default(service):
    """默认关闭：thinking.type = disabled"""
    body = service._thinking_body
    assert body == {"thinking": {"type": "disabled"}}


def test_thinking_body_enabled_when_configured(service, monkeypatch):
    """开启后：thinking.type = enabled"""
    monkeypatch.setattr(settings, "openai_thinking", True)
    body = service._thinking_body
    assert body == {"thinking": {"type": "enabled"}}


def test_thinking_body_disabled_when_false(service, monkeypatch):
    """显式关闭：thinking.type = disabled"""
    monkeypatch.setattr(settings, "openai_thinking", False)
    body = service._thinking_body
    assert body == {"thinking": {"type": "disabled"}}


def test_chat_passes_thinking_body_when_disabled(service, monkeypatch):
    """非流式调用时，extra_body 携带 disabled thinking"""
    captured = {}

    class _FakeClient:
        class chat:
            class completions:
                @staticmethod
                async def create(**kwargs):
                    captured.update(kwargs)
                    msg = type("M", (), {"content": "回答"})
                    return type("R", (), {"choices": [type("C", (), {"message": msg})]})

    monkeypatch.setattr("openai.AsyncOpenAI", lambda **kw: _FakeClient())

    asyncio.run(service.chat("你好", stream=False))
    assert captured.get("extra_body") == {"thinking": {"type": "disabled"}}
