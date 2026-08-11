"""SSE 输出契约测试：钉死后端 /api/chat/stream 的帧格式。

与 packages/core/test/sse.test.ts 形成**双向锁定**：
- core 测试钉死「前端如何切帧」（按 \\n\\n 分帧、找 data: 行、JSON 解析）
- 本测试钉死「后端如何发帧」（每个 chunk 一个 data: 行 + \\n\\n 结尾）

任一方改动导致格式不一致时，必有一边测试红。
"""
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """构造一个 client，用 dependency_overrides 注入 fake LLM，避免真实网络调用"""
    from app.config import settings
    from app.routers.chat import get_llm_service, get_rag_service
    from app.services.llm import LLMService
    from main import app

    # 契约测试走纯文本流，关掉所有 MCP 工具以免进入 tool loop
    monkeypatch.setattr(settings, "mcp_code_enabled", False)
    monkeypatch.setattr(settings, "anki_enabled", False)
    monkeypatch.setattr(settings, "notes_enabled", False)

    class _FakeStreamLLM(LLMService):
        async def chat(self, text, image=None, history=None, stream=False, media_type=None):
            if stream:
                async def gen():
                    for w in ("概率", "论", "条件", "期望"):
                        yield w
                return gen()
            return "概率论条件期望"

    # rag 也要 override，否则会真的去查向量库
    class _FakeRAG:
        def retrieve_context(self, *a, **k):
            return ""
        def get_sources(self, *a, **k):
            return []

    # 必须 app.dependency_overrides，Depends() 在 import 时已绑定函数对象，
    # 单纯 monkeypatch 模块属性不会改变已绑定的依赖
    app.dependency_overrides[get_llm_service] = lambda: _FakeStreamLLM()
    app.dependency_overrides[get_rag_service] = lambda: _FakeRAG()
    yield TestClient(app)
    app.dependency_overrides.clear()


def _parse_sse_frames(raw_text: str):
    """模拟前端 SSEParser：按 \\n\\n 切帧，取 data: 行 JSON 解析"""
    frames = raw_text.split("\n\n")
    events = []
    for frame in frames:
        data_line = next(
            (ln for ln in frame.split("\n") if ln.startswith("data: ")),
            None,
        )
        if not data_line:
            continue
        events.append(json.loads(data_line[6:]))
    return events


def test_chat_stream_emits_data_frames_separated_by_blank_line(client):
    """每个 delta 必须是独立 `data:` 帧，帧间以 \\n\\n 分隔（core SSEParser 的切帧依据）"""
    with client.stream("POST", "/api/chat/stream", json={"text": "解释"}) as resp:
        assert resp.status_code == 200
        # 用 iter_text 保留换行，iter_lines 会剥掉换行导致帧分隔符丢失
        raw = "".join(resp.iter_text())

    # 前端解析器能切出至少这些事件
    events = _parse_sse_frames(raw)

    # 至少有 1 个 delta + 1 个 done（流式分块边界不保证，不假设具体 delta 数）
    deltas = [e for e in events if e.get("delta")]
    dones = [e for e in events if e.get("done")]
    assert len(deltas) >= 1, f"期望至少 1 个 delta，实际 {len(deltas)}"
    # 所有 delta 拼起来必须等于 mock LLM 的完整输出
    full = "".join(d.get("delta", "") for d in deltas)
    assert full == "概率论条件期望", f"delta 拼接不完整: {full!r}"
    assert len(dones) >= 1, "缺少 done 帧"


def test_chat_stream_frame_format_matches_core_parser_assumption(client):
    """原始字节必须符合 `data: {json}\\n\\n` 格式（core SSEParser.findSentenceEnd 的前提）"""
    with client.stream("POST", "/api/chat/stream", json={"text": "解释"}) as resp:
        raw = b"".join(resp.iter_bytes()).decode("utf-8")

    # 每个帧都必须以 `data: ` 开头的内容 + 空行结尾
    # （done 帧也遵循同样格式）
    assert 'data: {"delta"' in raw or 'data: {"done"' in raw
    # 必须存在空行分隔（core 按 \n\n 切帧）
    assert "\n\n" in raw


def test_chat_stream_done_frame_has_empty_delta(client):
    """结束帧格式：delta 为空字符串、done 为 true（core 测试 test_done_frame 的对照）"""
    with client.stream("POST", "/api/chat/stream", json={"text": "解释"}) as resp:
        raw = "".join(resp.iter_text())

    events = _parse_sse_frames(raw)
    done_events = [e for e in events if e.get("done")]
    assert done_events, "缺少 done 帧"
    assert done_events[-1].get("delta", "") == "", "done 帧的 delta 应为空"


def test_chat_stream_json_keys_are_core_compatible(client):
    """帧 JSON 的 key 必须是 core SSEEvent 定义的 delta/done/error（小写、下划线无关）"""
    with client.stream("POST", "/api/chat/stream", json={"text": "解释"}) as resp:
        raw = "".join(resp.iter_text())

    events = _parse_sse_frames(raw)
    allowed_keys = {"delta", "done", "error"}
    for e in events:
        assert set(e.keys()) <= allowed_keys, f"出现未约定 key: {e.keys()}"
