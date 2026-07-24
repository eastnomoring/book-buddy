"""OpenAICompatibleService 消息构建测试（不发起网络请求）"""
import pytest

from app.config import settings
from app.services.llm import OpenAICompatibleService


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    return OpenAICompatibleService()


def test_build_messages_text_only(service):
    messages = service._build_messages("你好")
    assert messages == [{"role": "user", "content": "你好"}]


def test_build_messages_with_image(service):
    messages = service._build_messages("这页讲了什么？", image="aGVsbG8=")
    assert len(messages) == 1
    content = messages[0]["content"]
    assert content[0]["type"] == "image_url"
    assert content[0]["image_url"]["url"] == "data:image/jpeg;base64,aGVsbG8="
    assert content[1] == {"type": "text", "text": "这页讲了什么？"}


def test_build_messages_history_list_content_normalized(service):
    history = [
        {"role": "assistant", "content": [{"text": "回答一"}, {"text": "回答二"}]},
    ]
    messages = service._build_messages("追问", history=history)
    assert messages[0] == {"role": "assistant", "content": "回答一回答二"}
    assert messages[1] == {"role": "user", "content": "追问"}


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAICompatibleService()
