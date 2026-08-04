"""R2: 图片 mediaType 端到端透传测试。

验证 OpenAICompatibleService._build_messages 的 data URI 用传入的 media_type，
覆盖 png/jpeg/缺省三种情况。不发起网络请求。
"""
import pytest

from app.config import settings
from app.services.llm import OpenAICompatibleService


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    return OpenAICompatibleService()


def _image_url(messages):
    """从构建的消息中提取图片 data URI"""
    content = messages[-1]["content"]
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "image_url":
                return part["image_url"]["url"]
    return None


def test_build_messages_png_media_type(service):
    """PNG 图片：data URI 前缀为 image/png"""
    messages = service._build_messages("这页讲什么", image="pngdata", media_type="image/png")
    url = _image_url(messages)
    assert url is not None
    assert url.startswith("data:image/png;base64,pngdata")


def test_build_messages_jpeg_media_type(service):
    """JPEG 图片：data URI 前缀为 image/jpeg"""
    messages = service._build_messages("这页讲什么", image="jpegdata", media_type="image/jpeg")
    url = _image_url(messages)
    assert url is not None
    assert url.startswith("data:image/jpeg;base64,jpegdata")


def test_build_messages_default_falls_back_to_jpeg(service):
    """缺省 media_type：回退 image/jpeg（向后兼容旧客户端）"""
    messages = service._build_messages("这页讲什么", image="somedata")
    url = _image_url(messages)
    assert url is not None
    assert url.startswith("data:image/jpeg;base64,somedata")


def test_build_messages_webp_media_type(service):
    """WebP 图片（小程序相册可能选到）"""
    messages = service._build_messages("这页讲什么", image="webpdata", media_type="image/webp")
    url = _image_url(messages)
    assert url is not None
    assert url.startswith("data:image/webp;base64,webpdata")


def test_build_messages_no_image_ignores_media_type(service):
    """无图片时，media_type 不影响消息结构"""
    messages = service._build_messages("纯文本问题", media_type="image/png")
    assert messages[-1] == {"role": "user", "content": "纯文本问题"}
