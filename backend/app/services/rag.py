"""RAG 服务：书籍解析 + 向量检索"""
import hashlib
import re
from typing import List, Optional, Dict
from pathlib import Path

from app.config import settings


class BookParser:
    """书籍解析器：按页提取文本并按 chunk_size 分块"""

    def parse_pdf(self, file_path: str) -> List[Dict]:
        """
        解析 PDF 文件，返回分块列表

        Returns:
            [{"content": "...", "page": 1, "chapter": "..."}, ...]
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise RuntimeError(
                "缺少 PyMuPDF 依赖，请执行: pip install pymupdf"
            ) from e

        doc = fitz.open(file_path)
        chunks: List[Dict] = []
        chunk_size = settings.chunk_size
        chunk_overlap = min(settings.chunk_overlap, max(chunk_size - 1, 0))

        try:
            current_chapter = "正文"
            for page_index in range(len(doc)):
                page = doc[page_index]
                page_number = page_index + 1
                text = page.get_text("text") or ""
                text = self._normalize_text(text)
                if not text:
                    continue

                chapter = self._detect_chapter(text) or current_chapter
                current_chapter = chapter

                for piece in self._split_text(text, chunk_size, chunk_overlap):
                    chunks.append({
                        "content": piece,
                        "page": page_number,
                        "chapter": chapter,
                    })
        finally:
            doc.close()

        if not chunks:
            raise ValueError("PDF 未能提取到可用文本（可能是扫描版，需 OCR）")

        return chunks

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = text.replace("\x00", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _detect_chapter(text: str) -> Optional[str]:
        patterns = [
            r"^(第\s*[零一二三四五六七八九十百千\d]+\s*[章节回部])",
            r"^(Chapter\s+\d+)\b",
            r"^(CHAPTER\s+\d+)\b",
        ]
        head = text[:200]
        for pattern in patterns:
            match = re.search(pattern, head, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
        if len(text) <= chunk_size:
            return [text]

        pieces: List[str] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(start + chunk_size, length)
            # 尽量在段落/句号处断开
            if end < length:
                window = text[start:end]
                break_at = max(
                    window.rfind("\n\n"),
                    window.rfind("。"),
                    window.rfind(". "),
                    window.rfind("\n"),
                )
                if break_at >= chunk_size // 3:
                    end = start + break_at + 1

            piece = text[start:end].strip()
            if piece:
                pieces.append(piece)

            if end >= length:
                break
            start = max(end - overlap, start + 1)

        return pieces


class APIEmbeddingFunction:
    """通过 OpenAI 兼容接口调用云端嵌入模型（智谱 embedding-3 等）

    实现 Chroma EmbeddingFunction 协议（__call__ / name / 配置方法）。
    """

    # 智谱 embedding-3 单次请求最多 64 条
    BATCH_SIZE = 64

    def __init__(self):
        from openai import OpenAI

        if not settings.openai_api_key:
            raise ValueError("EMBEDDING_PROVIDER=openai 需要设置 OPENAI_API_KEY")
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.llm_timeout,
        )
        self._model = settings.embedding_model

    def name(self) -> str:
        return f"openai-compat-{self._model}"

    def __call__(self, input: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        texts = list(input)
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i:i + self.BATCH_SIZE]
            resp = self._client.embeddings.create(model=self._model, input=batch)
            embeddings.extend(item.embedding for item in resp.data)
        return embeddings

    def embed_documents(self, input: List[str]) -> List[List[float]]:
        return self(input)

    def embed_query(self, input: List[str]) -> List[List[float]]:
        return self(input)

    @staticmethod
    def build_from_config(config: dict) -> "APIEmbeddingFunction":
        return APIEmbeddingFunction()

    def get_config(self) -> dict:
        return {}


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
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            embedding_function = (
                APIEmbeddingFunction()
                if settings.embedding_provider == "openai"
                else None  # None = Chroma 默认本地模型（英文为主）
            )
            self.collection = client.get_or_create_collection(
                name="book_chunks",
                metadata={"hnsw:space": "cosine"},
                embedding_function=embedding_function,
            )
            self._initialized = True

        except Exception as e:
            raise RuntimeError(f"初始化向量库失败: {str(e)}") from e

    def invalidate(self) -> None:
        """标记向量库为未初始化，下次访问时按当前配置惰性重建。

        在 API Key / embedding 提供商变更后调用，使旧的 embedding
        函数（持有旧凭据）被丢弃，避免用旧配置继续检索。
        """
        self._initialized = False
        self.collection = None

    def add_chunks(self, chunks: List[Dict], book_id: str):
        """添加文档块到向量库（先清理同书旧数据）"""
        self._ensure_initialized()
        self.delete_book(book_id)

        ids = [
            f"{book_id}_{hashlib.md5(chunk['content'].encode('utf-8')).hexdigest()[:12]}_{i}"
            for i, chunk in enumerate(chunks)
        ]

        metadatas = [
            {
                "book_id": book_id,
                "page": int(chunk.get("page", 0) or 0),
                "chapter": str(chunk.get("chapter") or ""),
            }
            for chunk in chunks
        ]

        documents = [chunk["content"] for chunk in chunks]

        # Chroma 对单次 add 有大小限制，分批写入
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            self.collection.add(
                ids=ids[i:i + batch_size],
                documents=documents[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size],
            )

    def delete_book(self, book_id: str) -> None:
        """删除某本书的全部向量数据"""
        self._ensure_initialized()
        try:
            self.collection.delete(where={"book_id": book_id})
        except Exception:
            # 集合为空或不存在匹配项时忽略
            pass

    def search(
        self,
        query: str,
        book_id: Optional[str] = None,
        top_k: int = 5,
        chapter: Optional[str] = None,
        near_page: Optional[int] = None,
    ) -> List[Dict]:
        """检索相关文档块

        Args:
            chapter: 若提供，仅在该章节内检索（收窄当前页定位）
            near_page: 若提供，优先返回靠近该页的结果（同章节内按页码接近度加权）
        """
        self._ensure_initialized()

        if self.collection.count() == 0:
            return []

        # 构建过滤条件
        conditions = []
        if book_id:
            conditions.append({"book_id": book_id})
        if chapter:
            conditions.append({"chapter": chapter})

        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}
        else:
            where_filter = None

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k * 2, max(self.collection.count(), 1)),
                where=where_filter,
            )
        except Exception as e:
            print(f"向量检索失败: {e}")
            return []

        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        chunks = []
        for i, doc in enumerate(documents):
            meta = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else 1.0
            page = meta.get("page", 0)
            # near_page 加权：离目标页越近，score 越高
            page_boost = 0.0
            if near_page and isinstance(page, int) and page > 0:
                page_dist = abs(page - near_page)
                page_boost = max(0, 0.1 - page_dist * 0.005)  # 距离 20 页内有效
            chunks.append({
                "content": doc,
                "page": page,
                "chapter": meta.get("chapter", ""),
                "score": 1 - distance + page_boost,
            })

        # 按 score 降序，取 top_k
        chunks.sort(key=lambda c: c["score"], reverse=True)
        return chunks[:top_k]



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
        chunks = self.parser.parse_pdf(file_path)
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
        chapter: Optional[str] = None,
        near_page: Optional[int] = None,
    ) -> str:
        """检索相关上下文，返回拼接后的文本。

        传入 chapter/near_page 时收窄到该章节并按页码接近度加权（当前页定位用）。
        """
        chunks = self.vector_store.search(query, book_id, top_k, chapter=chapter, near_page=near_page)

        if not chunks:
            return ""

        context_parts = []
        for chunk in chunks:
            chapter_name = chunk.get("chapter") or ""
            header = f"[第 {chunk['page']} 页"
            if chapter_name:
                header += f" / {chapter_name}"
            header += "]"
            context_parts.append(f"{header}\n{chunk['content']}")

        return "\n\n".join(context_parts)

    def get_sources(
        self,
        query: str,
        book_id: Optional[str] = None,
        top_k: int = 3,
        chapter: Optional[str] = None,
        near_page: Optional[int] = None,
    ) -> List[Dict]:
        """获取引用来源（用于显示）"""
        return self.vector_store.search(query, book_id, top_k, chapter=chapter, near_page=near_page)

    def delete_book(self, book_id: str) -> None:
        """删除书籍向量数据"""
        self.vector_store.delete_book(book_id)


# 全局实例
rag_service = RAGService()
