"""S4: MCP tool loop 测试。

mock LLM 的 chat_with_tools，模拟「LLM 发起 tool_call → 执行 → 回注 → 最终回答」。
不触网，run_python 真实执行。
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.config import settings
from app.mcp.registry import registry
from app.mcp.tool_loop import run_chat_with_tools
from app.services.llm import OpenAICompatibleService


@pytest.fixture(autouse=True)
def _enable_code_tool(monkeypatch):
    """tool loop 测试需要把 run_python 暴露给 get_active_openai_tools"""
    monkeypatch.setattr(settings, "mcp_code_enabled", True)


def _tool_call_msg(tc_id, name, args):
    """构造 assistant 的 tool_calls 消息"""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": tc_id,
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)},
        }],
    }


def _tool_result_msg(tc_id, content):
    """构造 tool 角色的结果消息"""
    return {"role": "tool", "tool_call_id": tc_id, "content": content}


def _resp(content=None, tool_calls=None):
    """构造 LLM response"""
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


@pytest.fixture
def fake_llm(monkeypatch):
    """构造一个按脚本返回的 fake LLM"""
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    llm = OpenAICompatibleService()

    # 用队列控制每次 chat_with_tools 返回什么
    responses = []

    async def fake_chat_with_tools(messages, tools=None):
        if responses:
            return responses.pop(0)
        return _resp(content="（无更多响应）")

    monkeypatch.setattr(llm, "chat_with_tools", fake_chat_with_tools)
    return llm, responses


def test_tool_loop_single_round(fake_llm):
    """LLM 发起一次 tool_call → 执行 → 最终回答"""
    llm, responses = fake_llm

    # 第一次：LLM 要求执行代码
    responses.append(_resp(tool_calls=[SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="run_python", arguments=json.dumps({"code": "print(6*7)"})),
    )]))
    # 第二次：LLM 拿到结果后回答
    responses.append(_resp(content="42 是答案。"))

    result = asyncio.run(run_chat_with_tools(
        llm=llm,
        system_prompt="你是助手",
        user_text="6乘7是多少？用代码算",
    ))
    assert "42" in result


def test_tool_loop_no_tools_called(fake_llm):
    """LLM 直接回答，不调工具"""
    llm, responses = fake_llm
    responses.append(_resp(content="直接回答，不需要工具"))

    result = asyncio.run(run_chat_with_tools(
        llm=llm,
        system_prompt="你是助手",
        user_text="你好",
    ))
    assert result == "直接回答，不需要工具"


def test_tool_loop_max_rounds_cap(fake_llm):
    """超过最大轮次时收尾"""
    llm, responses = fake_llm

    # 连续 5 次要求 tool_call（MAX_TOOL_ROUNDS=5，循环内全消耗）
    for i in range(5):
        responses.append(_resp(tool_calls=[SimpleNamespace(
            id=f"call_{i}",
            function=SimpleNamespace(name="run_python", arguments=json.dumps({"code": f"print({i})"})),
        )]))
    # 第 6 次：无 tools 的收尾调用，返回纯文本
    responses.append(_resp(content="收尾回答"))

    result = asyncio.run(run_chat_with_tools(
        llm=llm,
        system_prompt="你是助手",
        user_text="循环测试",
    ))
    assert result == "收尾回答"


def test_tool_loop_unknown_tool_handled(fake_llm):
    """未知工具返回错误，不崩溃"""
    llm, responses = fake_llm
    responses.append(_resp(tool_calls=[SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="nonexistent_tool", arguments="{}"),
    )]))
    responses.append(_resp(content="工具不存在，直接回答"))

    result = asyncio.run(run_chat_with_tools(
        llm=llm,
        system_prompt="你是助手",
        user_text="测试",
    ))
    assert "直接回答" in result


def test_registry_has_run_python():
    """注册表里有 run_python 工具"""
    assert registry.has_tool("run_python")
    tools = registry.get_openai_tools()
    names = [t["function"]["name"] for t in tools]
    assert "run_python" in names
