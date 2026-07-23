"""书籍管理路由"""
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks

from app.models.chat import (
    BookInfo,
    BookUploadRequest,
    BookUploadResponse,
    BookSearchRequest,
    BookSearchResult,
)
from app.services.rag import rag_service

router = APIRouter()

# 内存中的书籍索引（后续可换成数据库）
books_db: dict[str, BookInfo] = {}


@router.post("/books/upload", response_model=BookUploadResponse)
async def upload_book(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    author: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
):
    """
    上传书籍 PDF
    
    后台解析并导入向量库
    """
    # 验证文件类型
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    
    # 生成书籍 ID
    book_id = str(uuid.uuid4())[:12]
    
    # 保存文件
    upload_dir = "./data/books"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{book_id}.pdf")
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # 记录书籍信息
    book_info = BookInfo(
        id=book_id,
        title=title or file.filename,
        author=author,
        total_pages=0,  # 解析后更新
    )
    books_db[book_id] = book_info
    
    # 后台解析
    async def parse_and_ingest():
        try:
            result = rag_service.ingest_book(file_path, book_id)
            books_db[book_id].total_pages = result["pages"]
        except Exception as e:
            print(f"书籍解析失败 [{book_id}]: {e}")
    
    if background_tasks:
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
    
    # 删除文件
    file_path = f"./data/books/{book_id}.pdf"
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # 删除记录
    del books_db[book_id]
    
    # TODO: 从向量库删除相关数据
    
    return {"message": "删除成功"}