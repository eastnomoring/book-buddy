"""笔记工具 + 活跃工具门控测试（Z2 收尾 / Z3 笔记部分）"""
import pytest
from pathlib import Path

from app.config import settings
from app.mcp.notes import _save_note, register_note_tool, NOTES_DIR
from app.mcp.registry import (
    registry,
    get_active_openai_tools,
    should_use_tool_loop,
    register_code_tool,
)


@pytest.fixture
def clean_notes(tmp_path, monkeypatch):
    """把笔记目录指到临时路径"""
    notes = tmp_path / "notes"
    notes.mkdir()
    monkeypatch.setattr("app.mcp.notes.NOTES_DIR", notes)
    return notes


def test_save_note_creates_markdown(clean_notes):
    result = _save_note(
        title="条件期望",
        content="E[X|Y] 的定义……",
        book="概率论读本",
        chapter="第3章",
        tags=["期望"],
    )
    assert result["images"] == []
    assert "笔记已保存" in result["text"]
    note_path = clean_notes / "概率论读本" / "第3章.md"
    assert note_path.exists()
    text = note_path.read_text(encoding="utf-8")
    assert "条件期望" in text
    assert "E[X|Y]" in text
    assert "title: 条件期望" in text


def test_save_note_appends_to_existing(clean_notes):
    _save_note(title="第一则", content="aaa", book="书", chapter="章")
    _save_note(title="第二则", content="bbb", book="书", chapter="章")
    note_path = clean_notes / "书" / "章.md"
    text = note_path.read_text(encoding="utf-8")
    assert "第一则" in text and "第二则" in text
    assert text.count("---") >= 2  # frontmatter + 分隔


def test_register_note_tool():
    register_note_tool()
    assert registry.has_tool("save_note")


def test_active_tools_gate_code_off_by_default(monkeypatch):
    """默认不暴露 run_python；笔记开启并注册后可走 tool loop"""
    monkeypatch.setattr(settings, "mcp_code_enabled", False)
    monkeypatch.setattr(settings, "anki_enabled", False)
    monkeypatch.setattr(settings, "notes_enabled", True)
    register_code_tool()
    register_note_tool()
    names = [t["function"]["name"] for t in get_active_openai_tools()]
    assert "run_python" not in names
    assert "save_note" in names
    assert should_use_tool_loop() is True


def test_active_tools_gate_code_on(monkeypatch):
    monkeypatch.setattr(settings, "mcp_code_enabled", True)
    monkeypatch.setattr(settings, "anki_enabled", False)
    register_code_tool()
    # 不注册笔记，仅代码
    # 清掉可能已有的 save_note：直接看 code 是否出现
    names = [t["function"]["name"] for t in get_active_openai_tools()]
    assert "run_python" in names
