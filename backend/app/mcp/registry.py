"""MCP 工具注册与调度。

首版采用「本地工具注册」而非「独立 MCP server 子进程通信」，
降低复杂度、便于测试。工具以统一接口注册，未来可平滑替换为
真正的 MCP stdio client（docs/MCP_CODE_EXECUTION_SELECTION.md §4）。

GLM-4.6V 的 Function Calling 用 OpenAI tools 协议：
LLM 返回 tool_calls → 后端执行 → 结果作为 tool 角色消息回注 → LLM 继续。
"""
import logging
from typing import Any, Callable

from app.mcp.code_executor import ExecutionResult, run_python

logger = logging.getLogger(__name__)


# ============ 工具注册 ============

ToolHandler = Callable[..., Any]


class ToolRegistry:
    """已注册工具的注册表"""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(
        self,
        name: str,
        description: str,
        params_schema: dict,
        handler: ToolHandler,
    ):
        """注册一个工具"""
        self._tools[name] = {
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": params_schema,
                },
            },
            "handler": handler,
        }

    def get_openai_tools(self) -> list[dict]:
        """返回 OpenAI tools 参数格式的工具列表"""
        return [t["schema"] for t in self._tools.values()]

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def call(self, name: str, arguments: dict) -> dict:
        """调用工具，返回 {text: str, images: list}。

        text 用于回注 LLM 和 tool_result.preview；
        images 为图片清单（可能为空），用于 tool_result.images。
        """
        if name not in self._tools:
            return {"text": f"错误：未知工具 {name}", "images": []}
        try:
            result = self._tools[name]["handler"](**arguments)
            if isinstance(result, ExecutionResult):
                return _format_exec_result(result)
            if isinstance(result, dict):
                return result  # 已是 {text, images} 格式
            return {"text": str(result), "images": []}
        except Exception as e:
            return {"text": f"工具执行错误: {e}", "images": []}


def _format_exec_result(result: ExecutionResult) -> dict:
    """把执行结果格式化为 LLM 可读的字符串 + 前端可读的图片清单"""
    parts = [f"exit_code: {result.exit_code}"]
    if result.timed_out:
        parts.append(f"⚠️ {result.stderr}")
    if result.stdout:
        parts.append(f"stdout:\n{result.stdout}")
    if result.stderr and not result.timed_out:
        parts.append(f"stderr:\n{result.stderr}")
    if result.images:
        parts.append(f"（生成了 {len(result.images)} 张图片）")
    text = "\n".join(parts)
    return {"text": text, "images": result.images}


# ============ 全局注册表 + 默认工具 ============

registry = ToolRegistry()

def register_code_tool() -> None:
    """注册 run_python（由 main lifespan 在 MCP_CODE_ENABLED=true 时调用）。"""
    if registry.has_tool("run_python"):
        return
    registry.register(
        name="run_python",
        description=(
            "执行 Python 代码并返回输出。用于数值模拟、概率验证、画图等。"
            "代码在受限沙箱中运行（超时10s、禁网络、256MB内存）。"
            "如：模拟抛硬币验证大数定律、计算期望方差、画分布图。"
        ),
        params_schema={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码",
                },
            },
            "required": ["code"],
        },
        handler=lambda code: run_python(code),
    )


def get_active_openai_tools() -> list[dict]:
    """按配置过滤当前应对 LLM 暴露的工具。

    - run_python：需 MCP_CODE_ENABLED
    - create_flashcard：需 ANKI_ENABLED 且已注册（AnkiConnect 可用）
    - save_note：已注册即暴露（零依赖本地笔记）
    """
    from app.config import settings

    allowed: set[str] = set()
    if settings.mcp_code_enabled and registry.has_tool("run_python"):
        allowed.add("run_python")
    if settings.anki_enabled and registry.has_tool("create_flashcard"):
        allowed.add("create_flashcard")
    if settings.notes_enabled and registry.has_tool("save_note"):
        allowed.add("save_note")

    return [
        t for t in registry.get_openai_tools()
        if t["function"]["name"] in allowed
    ]


def should_use_tool_loop(llm: Any = None) -> bool:
    """有任一活跃工具时走 tool loop（不再只看 MCP_CODE_ENABLED）。

    传入 llm 时额外检查其工具调用能力：tool loop 依赖 OpenAI tools 协议
    方法（chat_with_tools / stream_with_tools），目前仅 OpenAICompatibleService
    实现。qwen 等不支持的 provider 记 warning 并回退普通对话，保证聊天可用。
    """
    if not get_active_openai_tools():
        return False
    if llm is not None and not (
        hasattr(llm, "chat_with_tools") and hasattr(llm, "stream_with_tools")
    ):
        logger.warning(
            "当前 LLM 服务（%s）不支持工具调用，已注册的工具本次不生效，回退普通对话",
            type(llm).__name__,
        )
        return False
    return True


# 开发/测试便利：模块导入时预注册 run_python（生产仍由配置决定是否暴露）
register_code_tool()
