"""LLM 服务：通义千问 / DeepSeek 封装"""
import asyncio
from typing import Optional, AsyncIterator, List, Any, Union
from abc import ABC, abstractmethod

from app.config import settings


def extract_text_content(content: Any) -> str:
    """将 DashScope 多模态 content（str / list / dict）统一提取为纯文本。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or "")
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                text = getattr(item, "text", None)
                parts.append(str(text) if text is not None else "")
        return "".join(parts)
    text = getattr(content, "text", None)
    if text is not None:
        return str(text)
    return str(content)


class LLMService(ABC):
    """LLM 服务抽象基类"""

    @abstractmethod
    async def chat(
        self,
        text: str,
        image: Optional[str] = None,
        history: Optional[List[dict]] = None,
        stream: bool = False,
    ) -> Union[AsyncIterator[str], str]:
        """对话接口。stream=True 时返回异步迭代器，否则返回完整字符串。"""
        pass


class QwenVLService(LLMService):
    """通义千问 VL 服务"""

    def __init__(self):
        self.api_key = settings.dashscope_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout

        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 未设置")

    def _build_messages(
        self,
        text: str,
        image: Optional[str] = None,
        history: Optional[List[dict]] = None,
    ) -> List[dict]:
        messages: List[dict] = []

        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # 历史统一为纯文本，避免混入无法回放的多模态结构
                if isinstance(content, list):
                    content = extract_text_content(content)
                messages.append({"role": role, "content": content})

        if image:
            messages.append({
                "role": "user",
                "content": [
                    {"image": f"data:image/jpeg;base64,{image}"},
                    {"text": text},
                ],
            })
        else:
            messages.append({"role": "user", "content": text})

        return messages

    async def chat(
        self,
        text: str,
        image: Optional[str] = None,
        history: Optional[List[dict]] = None,
        stream: bool = False,
    ) -> Union[AsyncIterator[str], str]:
        """
        多模态对话

        Args:
            text: 用户输入文本
            image: 图像 base64（可选）
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]
            stream: 是否流式返回

        Returns:
            流式返回时为 AsyncIterator[str]，否则为完整回复字符串
        """
        import dashscope
        from dashscope import MultiModalConversation

        dashscope.api_key = self.api_key
        messages = self._build_messages(text, image, history)

        try:
            if stream:
                return self._stream_chat(MultiModalConversation, messages)

            response = await asyncio.to_thread(
                MultiModalConversation.call,
                model=self.model,
                messages=messages,
            )

            if response.status_code == 200:
                return extract_text_content(response.output.choices[0].message.content)
            raise Exception(f"LLM 错误: {response.code} - {response.message}")

        except Exception as e:
            if str(e).startswith("LLM 错误:") or str(e).startswith("调用通义千问失败:"):
                raise
            raise Exception(f"调用通义千问失败: {str(e)}") from e

    async def _stream_chat(self, MultiModalConversation, messages: List[dict]) -> AsyncIterator[str]:
        """流式生成；在阻塞读取间让出事件循环。"""
        # stream=True 时 call 立即返回同步生成器，迭代时才真正拉流
        responses = MultiModalConversation.call(
            model=self.model,
            messages=messages,
            stream=True,
        )

        full_content = ""
        for response in responses:
            if response.status_code == 200:
                content = extract_text_content(response.output.choices[0].message.content)
                if content and content != full_content:
                    # DashScope 流式通常返回累积全文，取增量
                    if content.startswith(full_content):
                        delta = content[len(full_content):]
                    else:
                        delta = content
                    full_content = content
                    if delta:
                        yield delta
            else:
                raise Exception(f"LLM 错误: {response.code} - {response.message}")
            await asyncio.sleep(0)


class OpenAICompatibleService(LLMService):
    """OpenAI 兼容接口服务（智谱 GLM / 硅基流动 / Ollama 通用）"""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url
        self.model = settings.openai_model
        self.timeout = settings.llm_timeout

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 未设置")

    @property
    def _thinking_body(self) -> dict:
        """GLM 思考模式 extra_body：enabled 时走 reasoning_content（适合复杂证明），
        disabled 时降低首字延迟（适合日常问答）。"""
        return {"thinking": {"type": "enabled" if settings.openai_thinking else "disabled"}}

    def _build_messages(
        self,
        text: str,
        image: Optional[str] = None,
        history: Optional[List[dict]] = None,
        media_type: Optional[str] = None,
    ) -> List[dict]:
        messages: List[dict] = []

        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # 历史统一为纯文本，避免混入无法回放的多模态结构
                if isinstance(content, list):
                    content = extract_text_content(content)
                messages.append({"role": role, "content": content})

        if image:
            # 用传入的 media_type 拼 data URI，缺省回退 jpeg（小程序相册可能选到 PNG/WebP）
            mt = media_type or "image/jpeg"
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mt};base64,{image}"},
                    },
                    {"type": "text", "text": text},
                ],
            })
        else:
            messages.append({"role": "user", "content": text})

        return messages

    async def chat(
        self,
        text: str,
        image: Optional[str] = None,
        history: Optional[List[dict]] = None,
        stream: bool = False,
        media_type: Optional[str] = None,
    ) -> Union[AsyncIterator[str], str]:
        """多模态对话，接口语义与 QwenVLService.chat 一致"""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        messages = self._build_messages(text, image, history, media_type)

        try:
            if stream:
                return self._stream_chat(client, messages)

            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                extra_body=self._thinking_body,
            )
            return response.choices[0].message.content or ""

        except Exception as e:
            raise Exception(f"调用 LLM 失败: {str(e)}") from e

    async def _stream_chat(self, client, messages: List[dict]) -> AsyncIterator[str]:
        """流式生成（OpenAI 返回增量 delta，直接透传）"""
        stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            extra_body=self._thinking_body,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def chat_with_tools(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
    ) -> Any:
        """带 tools 的非流式调用，返回原始 response（含 tool_calls）。

        供 MCP tool loop 使用。返回原始 response 对象，调用方自行处理
        content / tool_calls。
        """
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        kwargs = {
            "model": self.model,
            "messages": messages,
            "extra_body": self._thinking_body,
        }
        if tools:
            kwargs["tools"] = tools
        response = await client.chat.completions.create(**kwargs)
        return response

    async def stream_with_tools(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
    ):
        """带 tools 的流式调用，返回流式响应（AsyncIterator[chunk]）。

        供 MCP 流式 tool loop 使用。chunk 结构为 OpenAI 流式格式，
        tool_calls 可能分片，调用方需自行累积拼接。
        """
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        kwargs = {
            "model": self.model,
            "messages": messages,
            "extra_body": self._thinking_body,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
        return await client.chat.completions.create(**kwargs)


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例"""
    provider = settings.llm_provider

    if provider == "qwen":
        return QwenVLService()
    if provider == "openai":
        return OpenAICompatibleService()
    # DeepSeek VL 能力不成熟，已移除专用路径。
    # 如需用 DeepSeek 文本能力，走 openai 兼容接口（provider=openai，填 DeepSeek base_url）
    raise ValueError(
        f"不支持的 LLM 提供商: {provider}。可选: qwen | openai。"
        "DeepSeek 请用 openai 兼容接口（provider=openai + base_url 指向 DeepSeek）。"
    )
