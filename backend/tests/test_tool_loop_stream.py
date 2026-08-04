"""T1: 流式 tool loop 测试。

mock llm.stream_with_tools（对齐非流式 chat_with_tools 的测试做法），
验证事件序列：delta → tool_call → tool_result → delta → done。
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.config import settings
from app.mcp.tool_loop import run_chat_with_tools_stream
from app.services.llm import OpenAICompatibleService


@pytest.fixture(autouse=True)
def _enable_code_tool(monkeypatch):
    monkeypatch.setattr(settings, "mcp_code_enabled", True)


def _chunk(delta, finish_reason=None):
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice])


def _delta(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _tc(index, id=None, name=None, args=None):
    return SimpleNamespace(index=index, id=id, function=SimpleNamespace(name=name, arguments=args))


class _FakeStream:
    """自定义 async iterator，模拟 OpenAI 流式 chunk 序列"""

    def __init__(self, chunks):
        self._chunks = list(chunks)
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._chunks):
            raise StopAsyncIteration
        c = self._chunks[self._i]
        self._i += 1
        return c


async def _collect(gen):
    return [ev async for ev in gen]


@pytest.fixture
def fake_llm(monkeypatch):
    """构造带 mock stream_with_tools 的 LLM（返回 async iterator，模拟真实 AsyncStream）"""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    llm = OpenAICompatibleService()

    captured = {"tools": None, "rounds": 0}

    async def fake_stream_with_tools(messages, tools=None):
        captured["tools"] = tools
        captured["rounds"] += 1

        if captured["rounds"] == 1:
            args_part1 = '{"code": '
            args_part2 = '"print(42)"}'
            return _FakeStream([
                _chunk(_delta(content="让我算一下 ")),
                _chunk(_delta(tool_calls=[_tc(0, id="call_1", name="run_python", args=args_part1)])),
                _chunk(_delta(tool_calls=[_tc(0, args=args_part2)]), finish_reason="tool_calls"),
            ])
        return _FakeStream([
            _chunk(_delta(content="结果是 42。"), finish_reason="stop"),
        ])

    monkeypatch.setattr(llm, "stream_with_tools", fake_stream_with_tools)
    return llm, captured


def test_stream_event_sequence(fake_llm):
    """完整序列：delta → tool_call → tool_result → delta → done"""
    llm, _ = fake_llm
    events = asyncio.run(_collect(run_chat_with_tools_stream(
        llm=llm, system_prompt="你是助手", user_text="6乘7？",
    )))

    # 事件类型序列
    kinds = []
    for ev in events:
        if "type" in ev:
            kinds.append(ev["type"])
        elif ev.get("done"):
            kinds.append("done")
        else:
            kinds.append("delta")

    # 顺序校验：先 delta，再 tool_call，再 tool_result，最后 delta + done
    assert kinds[0] == "delta"
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert kinds[-1] == "done"

    # tool_call 结构
    tc = next(ev for ev in events if ev.get("type") == "tool_call")
    assert tc["name"] == "run_python"
    assert tc["id"] == "call_1"
    assert tc["arguments"] == {"code": "print(42)"}  # 分片拼接

    # tool_result 结构
    tr = next(ev for ev in events if ev.get("type") == "tool_result")
    assert tr["id"] == "call_1"
    assert "42" in tr["preview"]
    assert tr["ok"] is True

    # 收尾 delta 在 tool_result 之后
    deltas = [ev["delta"] for ev in events if "delta" in ev and ev.get("delta")]
    assert deltas[-1] == "结果是 42。"


def test_stream_passes_tools(fake_llm):
    """首次调用带 tools 参数"""
    llm, captured = fake_llm
    asyncio.run(_collect(run_chat_with_tools_stream(
        llm=llm, system_prompt="你是助手", user_text="测试",
    )))
    assert captured["tools"] is not None
    names = [t["function"]["name"] for t in captured["tools"]]
    assert "run_python" in names


def test_stream_done_format(fake_llm):
    """done 事件：delta 空 + done true"""
    llm, _ = fake_llm
    events = asyncio.run(_collect(run_chat_with_tools_stream(
        llm=llm, system_prompt="你是助手", user_text="测试",
    )))
    done_events = [ev for ev in events if ev.get("done")]
    assert done_events
    assert done_events[-1]["delta"] == ""


def test_stream_no_tools_called(fake_llm, monkeypatch):
    """LLM 直接回答不调工具"""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    llm = OpenAICompatibleService()

    async def fake_no_tools(messages, tools=None):
        return _FakeStream([
            _chunk(_delta(content="直接回答"), finish_reason="stop"),
        ])

    monkeypatch.setattr(llm, "stream_with_tools", fake_no_tools)

    events = asyncio.run(_collect(run_chat_with_tools_stream(
        llm=llm, system_prompt="你是助手", user_text="你好",
    )))
    kinds = ["tool_call" if ev.get("type") == "tool_call" else "done" if ev.get("done") else "delta" for ev in events]
    assert "tool_call" not in kinds
    assert kinds[-1] == "done"
