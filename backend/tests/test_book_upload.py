"""书籍上传接口测试：分块写入 + 大小限制（413）"""
import pytest
from fastapi.testclient import TestClient

from app.config import settings


@pytest.fixture
def client_and_dir(monkeypatch, tmp_path):
    """书籍目录指向临时路径，避免污染 data/books"""
    monkeypatch.setattr("app.routers.book.BOOKS_DIR", str(tmp_path))
    from main import app
    return TestClient(app), tmp_path


def test_upload_over_limit_returns_413(client_and_dir, monkeypatch):
    """超过 max_upload_mb 即中断写入并返回 413，不完整文件被清理"""
    client, books_dir = client_and_dir
    monkeypatch.setattr(settings, "max_upload_mb", 1)  # 1MB 上限

    big = b"%PDF-fake-" + b"x" * (1024 * 1024)  # 略超 1MB
    resp = client.post(
        "/api/books/upload",
        files={"file": ("big.pdf", big, "application/pdf")},
    )
    assert resp.status_code == 413
    assert "大小限制" in resp.json()["detail"]
    # 读取中途即中断：不应留下任何残留文件
    assert list(books_dir.iterdir()) == []


def test_upload_under_limit_accepted(client_and_dir):
    """限制内的小文件走完整流程（后台解析失败也被接口层吞掉）"""
    client, books_dir = client_and_dir
    from app.routers.book import books_db

    resp = client.post(
        "/api/books/upload",
        files={"file": ("small.pdf", b"%PDF-fake-small", "application/pdf")},
    )
    assert resp.status_code == 200
    book_id = resp.json()["id"]
    try:
        assert (books_dir / f"{book_id}.pdf").exists()
    finally:
        books_db.pop(book_id, None)
