"""MCP tool loop：LLM ↔ 工具的多轮交互。

非流式 /api/chat 启用 MCP 时调用。流程：
  1. 首次调用 LLM，带上 tools 参数
  2. 若 LLM 返回 tool_calls → 执行工具 → 结果作为 tool 消息回注
  3. 再次调用 LLM，循环直到无 tool_calls 或达到最大轮次
  4. 返回最终文本

最大轮次限制防止 LLM 无限调工具。
"""
import json
from typing import Optional, AsyncGenerator

from app.services.llm import LLMService
from app.mcp.registry import registry, get_active_openai_tools

MAX_TOOL_ROUNDS = 5


async def run_chat_with_tools(
    llm: LLMService,
    system_prompt: str,
    user_text: str,
    history: Optional[list] = None,
    image: Optional[str] = None,
    media_type: Optional[str] = None,
) -> str:
    """带工具调用的对话循环。

    Returns:
        LLM 最终文本回复
    """
    tools = get_active_openai_tools()

    # 构建初始消息
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history[-10:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    # 当前用户消息（含图）
    if image:
        from app.services.llm import extract_text_content
        # 多模态消息用 chat_with_tools 时手动构建
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{media_type or 'image/jpeg'};base64,{image}"}},
                {"type": "text", "text": user_text},
            ],
        })
    else:
        messages.append({"role": "user", "content": user_text})

    # tool loop
    for round_num in range(MAX_TOOL_ROUNDS):
        response = await llm.chat_with_tools(messages, tools)
        message = response.choices[0].message

        # 无 tool_calls → 返回最终文本
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            return message.content or ""

        # 有 tool_calls → 把 assistant 的 tool_calls 消息加入历史
        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ],
        })

        # 执行每个 tool_call，结果作为 tool 消息回注
        for tc in tool_calls:
            tool_name = tc.function.name
            try:
                arguments = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                arguments = {}

            result = registry.call(tool_name, arguments)
            # result 是 {text, images}；回注 LLM 只用 text
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result["text"],
            })

    # 超过最大轮次，做一次无 tools 调用收尾
    response = await llm.chat_with_tools(messages, tools=None)
    return response.choices[0].message.content or ""


async def run_chat_with_tools_stream(
    llm: LLMService,
    system_prompt: str,
    user_text: str,
    history: Optional[list] = None,
    image: Optional[str] = None,
    media_type: Optional[str] = None,
) -> AsyncGenerator:
    """带工具调用的流式对话循环（生成器）。

    逐条 yield 事件 dict（与 /chat/stream 的 SSE 帧直接对应）：
      {"delta": "文本", "done": false}           文本增量（不带 type，兼容旧前端）
      {"type": "tool_call", ...}                 工具调用发起
      {"type": "tool_result", ...}               工具执行结果
      {"delta": "", "done": true}                结束

    路由层直接把事件序列化为 SSE 帧。
    """
    import json as _json

    tools = get_active_openai_tools()

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history[-10:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    if image:
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{media_type or 'image/jpeg'};base64,{image}"}},
                {"type": "text", "text": user_text},
            ],
        })
    else:
        messages.append({"role": "user", "content": user_text})

    for round_num in range(MAX_TOOL_ROUNDS + 1):
        stream = await llm.stream_with_tools(messages, tools)

        # 累积本轮 assistant 回复
        collected_content = ""
        collected_tool_calls = {}  # index -> {id, name, arguments}
        finish_reason = None

        async for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            finish_reason = choice.finish_reason

            delta = choice.delta
            if delta is None:
                continue

            if delta.content:
                collected_content += delta.content
                yield {"delta": delta.content, "done": False}

            if getattr(delta, "tool_calls", None):
                for tc in delta.tool_calls:
                    idx = tc.index if tc.index is not None else 0
                    entry = collected_tool_calls.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        entry["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            entry["name"] = tc.function.name
                        if tc.function.arguments:
                            entry["arguments"] += tc.function.arguments

        # 本轮结束后：有 tool_calls → 执行工具；否则 → 结束
        tool_calls = list(collected_tool_calls.values())
        if not tool_calls:
            yield {"delta": "", "done": True}
            return

        # 把 assistant 消息（含 tool_calls）加入历史
        assistant_msg = {"role": "assistant", "content": collected_content or None}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"] or "{}"},
                }
                for tc in tool_calls
            ]
        messages.append(assistant_msg)

        # 逐个执行工具
        for tc in tool_calls:
            tool_name = tc.get("name", "")
            try:
                arguments = _json.loads(tc.get("arguments") or "{}")
            except _json.JSONDecodeError:
                arguments = {}

            yield {
                "type": "tool_call",
                "id": tc.get("id", ""),
                "name": tool_name,
                "arguments": arguments,
            }

            result = registry.call(tool_name, arguments)
            result_text = result["text"]
            result_images = result.get("images", [])
            ok = not result_text.startswith(("错误", "工具执行错误"))

            tool_result_event = {
                "type": "tool_result",
                "id": tc.get("id", ""),
                "name": tool_name,
                "preview": result_text[:1000],  # 截断预览，≤1KB
                "ok": ok,
            }
            # 有图时带 images 字段（向后兼容：无图时省略）
            if result_images:
                tool_result_event["images"] = result_images
            yield tool_result_event

            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result_text,
            })

    # 超过最大轮数：最后无 tools 收尾
    yield {"delta": "", "done": True}
