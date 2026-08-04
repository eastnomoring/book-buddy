"""Z2: Anki MCP 工具测试。

mock AnkiConnect HTTP 响应（httpx），不要求真装 Anki。
覆盖：ping、ensure_deck/model、add_note、AnkiConnect 不可用降级。
"""
import pytest
from unittest.mock import patch, MagicMock

from app.mcp.anki import AnkiConnectClient, _create_flashcard, register_anki_tool
from app.mcp.registry import registry


def _mock_response(json_data, status_code=200):
    """构造 mock httpx Response"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _anki_result(result=None, error=None):
    """构造 AnkiConnect 标准响应"""
    return {"result": result, "error": error}


def test_ping_success():
    """AnkiConnect 可用时 ping 返回 True"""
    client = AnkiConnectClient()
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_client.post.return_value = _mock_response(_anki_result(6))
        mock_client_cls.return_value = mock_client

        assert client.ping() is True


def test_ping_fail_when_anki_not_running():
    """AnkiConnect 不可用时 ping 返回 False"""
    client = AnkiConnectClient()
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_client.post.side_effect = Exception("connection refused")
        mock_client_cls.return_value = mock_client

        assert client.ping() is False


def test_add_note_creates_deck_and_model():
    """add_note 自动确保牌组和模型存在"""
    client = AnkiConnectClient()
    call_log = []

    def fake_post(url, json=None):
        call_log.append(json["action"])
        action = json["action"]
        if action == "version":
            return _mock_response(_anki_result(6))
        if action == "deckNames":
            return _mock_response(_anki_result(["Default"]))  # 不含 Book Buddy
        if action == "createDeck":
            return _mock_response(_anki_result(1))
        if action == "modelNames":
            return _mock_response(_anki_result(["Basic"]))  # 不含 BookBuddy Card
        if action == "createModel":
            return _mock_response(_anki_result(None))
        if action == "addNote":
            return _mock_response(_anki_result(123456789))
        return _mock_response(_anki_result(None))

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_client.post.side_effect = fake_post
        mock_client_cls.return_value = mock_client

        note_id = client.add_note("什么是期望？", "E[X]=∫xf(x)dx", "《概率论》p47", ["概率"])
        assert note_id == 123456789

    # 确认调了 createDeck + createModel + addNote
    assert "createDeck" in call_log
    assert "createModel" in call_log
    assert "addNote" in call_log


def test_add_note_skips_creation_when_exists():
    """牌组/模型已存在时不重复创建"""
    client = AnkiConnectClient()
    call_log = []

    def fake_post(url, json=None):
        action = json["action"]
        call_log.append(action)
        if action == "version":
            return _mock_response(_anki_result(6))
        if action == "deckNames":
            return _mock_response(_anki_result(["Default", "Book Buddy"]))  # 已含
        if action == "modelNames":
            return _mock_response(_anki_result(["Basic", "BookBuddy Card"]))  # 已含
        if action == "addNote":
            return _mock_response(_anki_result(999))
        return _mock_response(_anki_result(None))

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_client.post.side_effect = fake_post
        mock_client_cls.return_value = mock_client

        client.add_note("Q", "A")

    assert "createDeck" not in call_log  # 已存在，不创建
    assert "createModel" not in call_log
    assert "addNote" in call_log


def test_create_flashcard_graceful_when_anki_down():
    """AnkiConnect 不可用时返回明确错误，不崩溃"""
    with patch("app.mcp.anki.AnkiConnectClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.ping.return_value = False
        mock_cls.return_value = mock_client

        result = _create_flashcard(question="Q", answer="A")
        assert "Anki 未运行" in result["text"]
        assert result["images"] == []


def test_create_flashcard_success():
    """正常创建卡片返回成功信息"""
    with patch("app.mcp.anki.AnkiConnectClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.add_note.return_value = 12345
        mock_cls.return_value = mock_client

        result = _create_flashcard(
            question="什么是方差？",
            answer="Var(X) = E[(X-E[X])²]",
            source="《概率论》p52",
        )
        assert "已创建" in result["text"]
        assert "12345" in result["text"]


def test_register_anki_tool():
    """register_anki_tool 把 create_flashcard 加入 registry"""
    # 先确保没注册（可能被其他测试注册过）
    if registry.has_tool("create_flashcard"):
        # 已注册也算通过
        assert registry.has_tool("create_flashcard")
        return

    register_anki_tool()
    assert registry.has_tool("create_flashcard")
    tools = registry.get_openai_tools()
    names = [t["function"]["name"] for t in tools]
    assert "create_flashcard" in names
