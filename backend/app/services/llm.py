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


class DeepSeekService(LLMService):
    """DeepSeek 服务（占位实现）"""

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY 未设置")

    async def chat(
        self,
        text: str,
        image: Optional[str] = None,
        history: Optional[List[dict]] = None,
        stream: bool = False,
    ) -> Union[AsyncIterator[str], str]:
        """TODO: 实现 DeepSeek VL 调用"""
        raise NotImplementedError("DeepSeek 服务待实现")


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例"""
    provider = settings.llm_provider

    if provider == "qwen":
        return QwenVLService()
    if provider == "deepseek":
        return DeepSeekService()
    raise ValueError(f"不支持的 LLM 提供商: {provider}")
