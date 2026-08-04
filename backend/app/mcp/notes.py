"""笔记 MCP 工具：把讲解沉淀为本地 markdown 文件。

按书/章节目录组织，YAML frontmatter 记录元信息。
不依赖 Obsidian，纯文件即可用；Obsidian 用户可直接把 data/notes 作为 vault。

选型：本地文件写入，零依赖、可移植。搜索 MCP 另见 docs/SEARCH_MCP_SELECTION.md。
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.mcp.registry import registry

# 笔记根目录（与书籍数据同层）
NOTES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "notes"


def _safe_filename(name: str) -> str:
    """把书名/章节名转为安全的文件名"""
    # 保留中文、字母、数字、下划线、短横
    safe = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', name or "未命名")
    safe = re.sub(r'_+', '_', safe).strip('_')
    return safe or "未命名"


def _save_note(
    title: str,
    content: str,
    book: str = "",
    chapter: str = "",
    tags: Optional[list] = None,
) -> dict:
    """保存笔记为 markdown 文件。

    目录结构：data/notes/{book}/{chapter}.md
    如果同章节已有笔记，追加到文件末尾（以 --- 分隔）。
    """
    try:
        book_dir = NOTES_DIR / _safe_filename(book) if book else NOTES_DIR / "_通用"
        book_dir.mkdir(parents=True, exist_ok=True)

        chapter_name = _safe_filename(chapter) if chapter else "杂记"
        note_path = book_dir / f"{chapter_name}.md"

        # YAML frontmatter
        frontmatter_lines = [
            "---",
            f"title: {title}",
            f"book: {book}" if book else "book: ",
            f"chapter: {chapter}" if chapter else "chapter: ",
            f"created: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ]
        if tags:
            frontmatter_lines.append(f"tags: [{', '.join(tags)}]")
        frontmatter_lines.append("---\n")
        frontmatter = "\n".join(frontmatter_lines)

        note_body = f"## {title}\n\n{content}\n"

        # 文件不存在则新建（写 frontmatter），存在则追加
        if note_path.exists():
            with open(note_path, "a", encoding="utf-8") as f:
                f.write(f"\n---\n\n{note_body}")
        else:
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(f"{frontmatter}{note_body}")

        rel_path = note_path.relative_to(NOTES_DIR.parent)
        return {
            "text": f"✅ 笔记已保存到 {rel_path}（{title}）",
            "images": [],
        }
    except Exception as e:
        return {"text": f"保存笔记失败: {e}", "images": []}


def register_note_tool():
    """注册笔记工具到 registry"""
    registry.register(
        name="save_note",
        description=(
            "把讲解内容保存为 markdown 笔记，按书/章节归档。"
            "适合在详细解释完一个知识点后调用，便于日后复习。"
            "内容支持 markdown 语法（标题、列表、加粗、代码块、LaTeX 公式）。"
        ),
        params_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "笔记标题（知识点名称）"},
                "content": {
                    "type": "string",
                    "description": "笔记正文（markdown，可含公式、列表等）",
                },
                "book": {"type": "string", "description": "书名（如《概率论读本》）"},
                "chapter": {"type": "string", "description": "章节（如「第3章 连续随机变量」）"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "标签"},
            },
            "required": ["title", "content"],
        },
        handler=_save_note,
    )
