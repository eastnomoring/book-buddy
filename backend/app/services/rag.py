"""RAG 服务：书籍解析 + 向量检索"""
import os
import hashlib
from typing import List, Optional, Dict
from pathlib import Path

from app.config import settings


class BookParser:
    """书籍解析器"""
    
    def parse_pdf(self, file_path: str) -> List[Dict]:
        """
        解析 PDF 文件，返回分块列表
        
        Returns:
            [{"content": "...", "page": 1, "chapter": "..."}, ...]
        """
        # TODO: 使用 marker 或 nougat 解析
        # 当前返回占位实现
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 占位：实际需要用 marker 库解析
        # from marker.converters.pdf import PdfConverter
        # from marker.models import load_all_models
        
        return [
            {
                "content": f"这是第 {i} 页的示例内容，实际需要用 marker 解析 PDF。",
                "page": i,
                "chapter": f"第 {i // 10 + 1} 章",
            }
            for i in range(1, 11)
        ]


class VectorStore:
    """向量存储"""
    
    def __init__(self, persist_dir: str = None):
        self.persist_dir = persist_dir or settings.vector_db_path
        self.collection = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """确保向量库已初始化"""
        if self._initialized:
            return
        
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            self.collection = client.get_or_create_collection(
                name="book_chunks",
                metadata={"hnsw:space": "cosine"}
            )
            self._initialized = True
            
        except Exception as e:
            raise RuntimeError(f"初始化向量库失败: {str(e)}")
    
    def add_chunks(self, chunks: List[Dict], book_id: str):
        """添加文档块到向量库"""
        self._ensure_initialized()
        
        ids = [
            f"{book_id}_{hashlib.md5(chunk['content'].encode()).hexdigest()[:12]}"
            for chunk in chunks
        ]
        
        metadatas = [
            {
                "book_id": book_id,
                "page": chunk.get("page", 0),
                "chapter": chunk.get("chapter", ""),
            }
            for chunk in chunks
        ]
        
        documents = [chunk["content"] for chunk in chunks]
        
        # 生成嵌入（使用 Chroma 内置的 embedding 函数）
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
    
    def search(
        self,
        query: str,
        book_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        """检索相关文档块"""
        self._ensure_initialized()
        
        where_filter = None
        if book_id:
            where_filter = {"book_id": book_id}
        
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
        )
        
        # 格式化结果
        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            chunks.append({
                "content": doc,
                "page": results["metadatas"][0][i].get("page", 0),
                "chapter": results["metadatas"][0][i].get("chapter", ""),
                "score": 1 - results["distances"][0][i],  # 转换为相似度
            })
        
        return chunks


class RAGService:
    """RAG 服务：整合解析和检索"""
    
    def __init__(self):
        self.parser = BookParser()
        self.vector_store = VectorStore()
    
    def ingest_book(self, file_path: str, book_id: str) -> Dict:
        """
        导入书籍到向量库
        
        Returns:
            {"total_chunks": 100, "pages": 200}
        """
        # 解析 PDF
        chunks = self.parser.parse_pdf(file_path)
        
        # 添加到向量库
        self.vector_store.add_chunks(chunks, book_id)
        
        return {
            "total_chunks": len(chunks),
            "pages": max(c["page"] for c in chunks) if chunks else 0,
        }
    
    def retrieve_context(
        self,
        query: str,
        book_id: Optional[str] = None,
        top_k: int = 5,
    ) -> str:
        """
        检索相关上下文，返回拼接后的文本
        """
        chunks = self.vector_store.search(query, book_id, top_k)
        
        if not chunks:
            return ""
        
        context_parts = []
        for chunk in chunks:
            context_parts.append(
                f"[第 {chunk['page']} 页]\n{chunk['content']}"
            )
        
        return "\n\n".join(context_parts)
    
    def get_sources(
        self,
        query: str,
        book_id: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict]:
        """获取引用来源（用于显示）"""
        return self.vector_store.search(query, book_id, top_k)


# 全局实例
rag_service = RAGService()