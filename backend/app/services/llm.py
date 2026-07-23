"""LLM 服务：通义千问 / DeepSeek 封装"""
import base64
import json
from typing import Optional, AsyncIterator, List
from abc import ABC, abstractmethod

from app.config import settings


class LLMService(ABC):
    """LLM 服务抽象基类"""
    
    @abstractmethod
    async def chat(
        self,
        text: str,
        image: Optional[str] = None,
        history: Optional[List[dict]] = None,
        stream: bool = False,
    ) -> AsyncIterator[str] | str:
        """对话接口"""
        pass


class QwenVLService(LLMService):
    """通义千问 VL 服务"""
    
    def __init__(self):
        self.api_key = settings.dashscope_api_key
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout
        
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 未设置")
    
    async def chat(
        self,
        text: str,
        image: Optional[str] = None,
        history: Optional[List[dict]] = None,
        stream: bool = False,
    ) -> AsyncIterator[str] | str:
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
        
        # 构建消息
        messages = []
        
        # 添加历史
        if history:
            messages.extend(history)
        
        # 当前消息
        if image:
            # 多模态消息：图像 + 文本
            user_message = {
                "role": "user",
                "content": [
                    {"image": f"data:image/jpeg;base64,{image}"},
                    {"text": text}
                ]
            }
        else:
            user_message = {"role": "user", "content": text}
        
        messages.append(user_message)
        
        try:
            if stream:
                # 流式调用
                responses = MultiModalConversation.call(
                    model=self.model,
                    messages=messages,
                    stream=True,
                )
                
                async def stream_generator():
                    full_content = ""
                    for response in responses:
                        if response.status_code == 200:
                            content = response.output.choices[0].message.content
                            if content and content != full_content:
                                delta = content[len(full_content):]
                                full_content = content
                                yield delta
                        else:
                            raise Exception(f"LLM 错误: {response.code} - {response.message}")
                
                return stream_generator()
            else:
                # 非流式调用
                response = MultiModalConversation.call(
                    model=self.model,
                    messages=messages,
                )
                
                if response.status_code == 200:
                    return response.output.choices[0].message.content
                else:
                    raise Exception(f"LLM 错误: {response.code} - {response.message}")
                    
        except Exception as e:
            raise Exception(f"调用通义千问失败: {str(e)}")


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
    ) -> AsyncIterator[str] | str:
        """TODO: 实现 DeepSeek VL 调用"""
        raise NotImplementedError("DeepSeek 服务待实现")


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例"""
    provider = settings.llm_provider
    
    if provider == "qwen":
        return QwenVLService()
    elif provider == "deepseek":
        return DeepSeekService()
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")