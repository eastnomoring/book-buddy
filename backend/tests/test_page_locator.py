"""S3: 当前页定位 MVP 测试。

覆盖 page_locator 的 JSON 提取容错，以及 chat 路由的
「识别成功收窄 RAG」「识别失败降级整书 RAG」两条路径。
VLM 与 RAG 全部 mock，不触网。
"""
import json
import pytest
from fastapi.testclient import TestClient

from app.services.page_locator import _extract_json


# ============ _extract_json 容错测试 ============

def test_extract_json_plain():
    assert _extract_json('{"page": 47, "chapter": "第3章"}') == {"page": 47, "chapter": "第3章"}


def test_extract_json_code_block():
    text = '```json\n{"page": 12, "chapter": null}\n```'
    result = _extract_json(text)
    assert result["page"] == 12


def test_extract_json_with_surrounding_text():
    text = '好的，识别结果如下：{"page": 88, "chapter": "极限"} 希望有帮助'
    result = _extract_json(text)
    assert result["page"] == 88


def test_extract_json_invalid_returns_empty():
    assert _extract_json("这不是JSON") == {}
    assert _extract_json("") == {}


# ============ chat 路由的页码定位收窄/降级测试 ============

@pytest.fixture
def mock_app(monkeypatch):
    """构造带 mock LLM/RAG 的 app"""
    from main import app
    from app.routers.chat import get_llm_service, get_rag_service
    from app.services.llm import LLMService
    from app.services.page_locator import locate_page
    from app.config import settings

    monkeypatch.setattr(settings, "mcp_code_enabled", False)
    monkeypatch.setattr(settings, "anki_enabled", False)
    monkeypatch.setattr(settings, "notes_enabled", False)

    call_log = {"locate": False, "rag_chapter": None, "rag_near_page": None}

    class _FakeLLM(LLMService):
        async def chat(self, text, image=None, history=None, stream=False, media_type=None):
            if stream:
                async def gen():
                    yield "回答"
                return gen()
            return "完整回答"

    class _FakeRAG:
        def retrieve_context(self, query, book_id=None, top_k=5, chapter=None, near_page=None):
            call_log["rag_chapter"] = chapter
            call_log["rag_near_page"] = near_page
            return f"[上下文 chapter={chapter} page={near_page}]"

        def get_sources(self, *a, **k):
            return []

    app.dependency_overrides[get_llm_service] = lambda: _FakeLLM()
    app.dependency_overrides[get_rag_service] = lambda: _FakeRAG()

    # mock locate_page：第一次成功，第二次返回空（降级）
    async def fake_locate_success(llm, image, media_type=None):
        call_log["locate"] = True
        return {"page": 47, "chapter": "第3章"}

    async def fake_locate_fail(llm, image, media_type=None):
        call_log["locate"] = True
        return {}

    yield app, call_log, fake_locate_success, fake_locate_fail
    app.dependency_overrides.clear()


def test_chat_locates_page_and_narrows_rag(mock_app, monkeypatch):
    """识别成功：RAG 收窄到识别出的 chapter + near_page"""
    app, call_log, locate_success, _ = mock_app
    monkeypatch.setattr("app.routers.chat.locate_page", locate_success)

    client = TestClient(app)
    resp = client.post("/api/chat", json={
        "text": "这页讲什么",
        "image": "base64data",
        "book_id": "book-1",
    })

    assert resp.status_code == 200
    assert call_log["locate"] is True
    assert call_log["rag_chapter"] == "第3章"
    assert call_log["rag_near_page"] == 47


def test_chat_degrades_when_location_fails(mock_app, monkeypatch):
    """识别失败：降级为整书 RAG（chapter=None, near_page=None）"""
    app, call_log, _, locate_fail = mock_app
    monkeypatch.setattr("app.routers.chat.locate_page", locate_fail)

    client = TestClient(app)
    resp = client.post("/api/chat", json={
        "text": "这页讲什么",
        "image": "base64data",
        "book_id": "book-1",
    })

    assert resp.status_code == 200
    assert call_log["rag_chapter"] is None
    assert call_log["rag_near_page"] is None


def test_chat_skips_location_without_image(mock_app, monkeypatch):
    """无图片时不做页码定位，走整书 RAG"""
    app, call_log, locate_success, _ = mock_app
    monkeypatch.setattr("app.routers.chat.locate_page", locate_success)

    client = TestClient(app)
    resp = client.post("/api/chat", json={
        "text": "纯文本问题",
        "book_id": "book-1",
    })

    assert resp.status_code == 200
    assert call_log["locate"] is False  # 没调 locate_page


def test_chat_skips_location_without_book(mock_app, monkeypatch):
    """无 book_id 时不做页码定位"""
    app, call_log, locate_success, _ = mock_app
    monkeypatch.setattr("app.routers.chat.locate_page", locate_success)

    client = TestClient(app)
    resp = client.post("/api/chat", json={
        "text": "问题",
        "image": "base64data",
        # 无 book_id
    })

    assert resp.status_code == 200
    assert call_log["locate"] is False
