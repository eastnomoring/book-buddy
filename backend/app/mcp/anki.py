"""AnkiConnect 客户端 + MCP 工具。

自建薄客户端直连 AnkiConnect HTTP API（localhost:8765），
不引入 ankimcp server（过重）。选型见 docs/ANKI_MCP_SELECTION.md。

用户侧前置：装 Anki + AnkiConnect 插件（码 2055492159），保持 Anki 开启。
"""
import json
from typing import Optional

import httpx

ANKI_CONNECT_URL = "http://localhost:8765"
DEFAULT_DECK = "Book Buddy"
MODEL_NAME = "BookBuddy Card"


class AnkiConnectClient:
    """AnkiConnect HTTP API 薄封装"""

    def __init__(self, url: str = ANKI_CONNECT_URL, timeout: int = 5):
        self.url = url
        self.timeout = timeout

    def _invoke(self, action: str, **params) -> dict:
        """调用 AnkiConnect action"""
        payload = {"action": action, "version": 6, "params": params}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self.url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if data.get("error"):
                raise RuntimeError(f"AnkiConnect 错误: {data['error']}")
            return data.get("result")

    def ping(self) -> bool:
        """检查 AnkiConnect 是否可用"""
        try:
            result = self._invoke("version")
            return isinstance(result, int)
        except Exception:
            return False

    def ensure_deck(self, deck_name: str = DEFAULT_DECK) -> None:
        """确保牌组存在（不存在则创建）"""
        decks = self._invoke("deckNames")
        if deck_name not in decks:
            self._invoke("createDeck", deck=deck_name)

    def ensure_model(self) -> None:
        """确保自定义模型 BookBuddy Card 存在（不存在则创建）"""
        models = self._invoke("modelNames")
        if MODEL_NAME in models:
            return

        self._invoke("createModel", **{
            "modelName": MODEL_NAME,
            "inOrderFields": ["Question", "Source", "Answer"],
            "cardTemplates": [{
                "Name": "BookBuddy Card",
                "Front": '{{Question}}<br><small style="color:#888">{{Source}}</small>',
                "Back": '{{FrontSide}}<hr id=answer>{{Answer}}',
            }],
            "css": ".card { font-family: sans-serif; font-size: 18px; text-align: center; }",
        })

    def add_note(
        self,
        question: str,
        answer: str,
        source: str = "",
        tags: Optional[list] = None,
        deck: str = DEFAULT_DECK,
    ) -> int:
        """创建一张卡片，返回 note id"""
        self.ensure_deck(deck)
        self.ensure_model()

        note = {
            "deckName": deck,
            "modelName": MODEL_NAME,
            "fields": {
                "Question": question,
                "Source": source,
                "Answer": answer,
            },
            "tags": tags or [],
            "options": {"allowDuplicate": True},
        }
        result = self._invoke("addNote", note=note)
        if not result:
            raise RuntimeError("添加卡片失败（可能内容重复且未允许重复）")
        return result

    def deck_names(self) -> list:
        """列出所有牌组名"""
        return self._invoke("deckNames")


# ============ MCP 工具注册 ============

from app.mcp.registry import registry


def _create_flashcard(
    question: str,
    answer: str,
    source: str = "",
    tags: Optional[list] = None,
) -> dict:
    """创建 Anki 卡片的工具处理器"""
    client = AnkiConnectClient()
    if not client.ping():
        return {"text": "⚠️ Anki 未运行或未安装 AnkiConnect 插件（码 2055492159）。卡片未创建。", "images": []}

    try:
        note_id = client.add_note(question, answer, source, tags)
        return {
            "text": f"✅ 已创建 Anki 卡片（id: {note_id}）。正面：{question[:60]}",
            "images": [],
        }
    except Exception as e:
        return {"text": f"创建卡片失败: {e}", "images": []}


def register_anki_tool():
    """注册 Anki 工具到 registry（仅 ANKI_ENABLED 时由调用方触发）"""
    registry.register(
        name="create_flashcard",
        description=(
            "创建一张 Anki 抽认卡用于间隔重复复习。学完一个知识点后调用。"
            "需要用户本地运行 Anki + AnkiConnect 插件。"
            "LaTeX 公式用 [$]...[$] 包裹（Anki 原生支持）。"
        ),
        params_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "正面问题（简洁明了）"},
                "answer": {
                    "type": "string",
                    "description": "背面讲解，可含 LaTeX（[$]x^2[$]）、列表、加粗等",
                },
                "source": {"type": "string", "description": "出处：书名+页码/章节，如《概率论》第47页"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "标签列表"},
            },
            "required": ["question", "answer"],
        },
        handler=_create_flashcard,
    )
