"""当前页定位服务：用 VLM 识别书页页码/章节，收窄 RAG 检索。

这是「伴学」区别于「问答机器人」的核心体验（HANDOFF §4 难点 2）。
拍照后先做一次轻量 VLM 调用，只要求返回页码或章节标题，
再用识别结果收窄 RAG 到该章/页附近。
"""
import json
import re
from typing import Optional

from app.services.llm import LLMService


# 识别用的 prompt：只要求返回 JSON，不带推理，降低延迟
LOCATE_PROMPT = """请观察这张书页图片，识别它属于哪一页、哪一章。
只返回一个 JSON，不要解释。格式：{"page": 页码数字或null, "chapter": "章节标题或null"}
- page：页面上印刷的页码（通常在页脚/页眉）。找不到就是 null
- chapter：当前所属章节标题（如"第3章 连续随机变量"）。找不到就是 null"""


def _extract_json(text: str) -> dict:
    """从 VLM 回复中提取 JSON（容错：可能有 ```json 包裹或多余文字）"""
    # 尝试直接解析
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试提取第一个 {...}
    match = re.search(r"\{[^{}]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


async def locate_page(
    llm: LLMService,
    image_base64: str,
    media_type: Optional[str] = None,
) -> dict:
    """识别书页的页码与章节。

    Returns:
        {"page": Optional[int], "chapter": Optional[str]}
        识别失败时返回空 dict，调用方应降级为整书 RAG。
    """
    try:
        response = await llm.chat(
            text=LOCATE_PROMPT,
            image=image_base64,
            media_type=media_type,
            stream=False,
        )
        if not isinstance(response, str):
            return {}

        data = _extract_json(response)

        # 规范化：page 转 int 或 None，chapter 转 str 或 None
        page = data.get("page")
        if page is not None:
            try:
                page = int(page)
            except (ValueError, TypeError):
                page = None

        chapter = data.get("chapter")
        if chapter in ("null", ""):
            chapter = None

        result = {}
        if page and page > 0:
            result["page"] = page
        if chapter:
            result["chapter"] = str(chapter)
        return result

    except Exception as e:
        print(f"页码识别失败，降级为整书 RAG: {e}")
        return {}
