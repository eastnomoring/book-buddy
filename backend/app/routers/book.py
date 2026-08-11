"""书籍管理路由"""
import logging
import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.config import settings
from app.models.chat import (
    BookInfo,
    BookSearchRequest,
    BookSearchResult,
    BookUploadResponse,
)
from app.services.rag import rag_service

logger = logging.getLogger(__name__)

router = APIRouter()

# 书籍存储目录
BOOKS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "books")
BOOKS_DIR = os.path.abspath(BOOKS_DIR)

# 上传分块大小（1MB）：边读边写，超限即中断，不整文件入内存
UPLOAD_CHUNK_BYTES = 1024 * 1024


def _meta_path(book_id: str) -> str:
    """书籍元信息 sidecar 路径（与 PDF 同名，扩展名 .json）"""
    return os.path.join(BOOKS_DIR, f"{book_id}.json")


def _save_meta(book_info: BookInfo) -> None:
    """把书籍元信息落盘，供重启后重建索引"""
    os.makedirs(BOOKS_DIR, exist_ok=True)
    with open(_meta_path(book_info.id), "w", encoding="utf-8") as f:
        f.write(book_info.model_dump_json())


def _load_meta(book_id: str) -> Optional[BookInfo]:
    path = _meta_path(book_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return BookInfo.model_validate_json(f.read())
    except Exception as e:
        logger.warning("读取书籍元信息失败 [%s]: %s", book_id, e)
        return None


def rebuild_books_index() -> int:
    """启动时从磁盘重建内存索引（books_db）。

    扫描 data/books 下的 *.json 元信息文件并载入。
    向量数据由 Chroma 持久化，无需重建；total_pages 若未持久化，
    尝试用向量库中该书的最大页码回填。
    """
    os.makedirs(BOOKS_DIR, exist_ok=True)
    count = 0
    for entry in os.scandir(BOOKS_DIR):
        if not entry.name.endswith(".json"):
            continue
        book_id = entry.name[:-len(".json")]
        info = _load_meta(book_id)
        if info is None:
            continue
        # 若解析未完成就被重启，total_pages 可能是 0，用向量库回填
        if info.total_pages <= 0:
            try:
                chunks = rag_service.vector_store.search("任何内容", book_id, top_k=1)
                if chunks:
                    info.total_pages = max(c["page"] for c in chunks)
            except Exception:
                pass
        books_db[book_id] = info
        count += 1
    return count


# 内存中的书籍索引（启动时由 rebuild_books_index 从磁盘重建）
books_db: dict[str, BookInfo] = {}


@router.post("/books/upload", response_model=BookUploadResponse)
async def upload_book(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
):
    """
    上传书籍 PDF

    后台解析并导入向量库
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")

    book_id = str(uuid.uuid4())[:12]

    os.makedirs(BOOKS_DIR, exist_ok=True)

    file_path = os.path.join(BOOKS_DIR, f"{book_id}.pdf")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    written = 0
    try:
        with open(file_path, "wb") as f:
            while chunk := await file.read(UPLOAD_CHUNK_BYTES):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件超过大小限制（最大 {settings.max_upload_mb}MB）",
                    )
                f.write(chunk)
    except Exception:
        # 清理不完整的上传产物
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    if written == 0:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="上传文件为空")

    book_title = title or file.filename
    book_info = BookInfo(
        id=book_id,
        title=book_title,
        author=author,
        total_pages=0,
    )
    books_db[book_id] = book_info
    _save_meta(book_info)

    def parse_and_ingest():
        try:
            result = rag_service.ingest_book(file_path, book_id)
            if book_id in books_db:
                books_db[book_id].total_pages = result["pages"]
                _save_meta(books_db[book_id])
        except Exception as e:
            logger.warning("书籍解析失败 [%s]: %s", book_id, e)
            if book_id in books_db:
                # 保留记录但页数为 -1 表示解析失败
                books_db[book_id].total_pages = -1
                _save_meta(books_db[book_id])

    background_tasks.add_task(parse_and_ingest)

    return BookUploadResponse(
        id=book_id,
        title=book_info.title,
        message="书籍上传成功，正在后台解析...",
    )


@router.get("/books", response_model=List[BookInfo])
async def list_books():
    """列出所有书籍"""
    return list(books_db.values())


@router.get("/books/{book_id}", response_model=BookInfo)
async def get_book(book_id: str):
    """获取书籍详情"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="书籍不存在")

    return books_db[book_id]


@router.post("/books/search", response_model=List[BookSearchResult])
async def search_book(request: BookSearchRequest):
    """在书籍中检索"""
    chunks = rag_service.vector_store.search(
        query=request.query,
        book_id=request.book_id,
        top_k=request.top_k,
    )

    return [
        BookSearchResult(
            content=chunk["content"],
            page=chunk["page"],
            chapter=chunk.get("chapter"),
            score=chunk.get("score", 0),
        )
        for chunk in chunks
    ]


@router.delete("/books/{book_id}")
async def delete_book(book_id: str):
    """删除书籍"""
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="书籍不存在")

    # 清理 PDF、元信息、向量数据
    for ext in (".pdf", ".json"):
        path = os.path.join(BOOKS_DIR, f"{book_id}{ext}")
        if os.path.exists(path):
            os.remove(path)

    del books_db[book_id]
    rag_service.delete_book(book_id)

    return {"message": "删除成功"}
