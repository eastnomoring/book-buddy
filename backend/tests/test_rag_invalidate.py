"""VectorStore.invalidate 与书籍索引重建测试（不碰网络与真实向量库）"""
import json

import pytest

from app.services.rag import VectorStore
from app.routers.book import rebuild_books_index, books_db, _save_meta
from app.models.chat import BookInfo


def test_invalidate_resets_state():
    vs = VectorStore(persist_dir="/tmp/book-buddy-test-invalidate")
    # 模拟已初始化的状态
    vs._initialized = True
    vs.collection = "fake-collection"
    vs.invalidate()
    assert vs._initialized is False
    assert vs.collection is None


def test_rebuild_books_index_restores_meta(tmp_path, monkeypatch):
    import app.routers.book as book_router

    # 把书籍目录指向临时目录
    monkeypatch.setattr(book_router, "BOOKS_DIR", str(tmp_path))

    info = BookInfo(id="abc123", title="测试书", total_pages=42)
    _save_meta(info)

    # 写入 sidecar 到临时目录
    meta_path = tmp_path / "abc123.json"
    meta_path.write_text(info.model_dump_json(), encoding="utf-8")

    # 清空内存索引后重建
    books_db.clear()
    n = rebuild_books_index()
    assert n == 1
    assert "abc123" in books_db
    assert books_db["abc123"].title == "测试书"
    assert books_db["abc123"].total_pages == 42
