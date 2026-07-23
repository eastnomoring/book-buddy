"""PDF 分块逻辑测试（不依赖真实 PDF 文件）"""
from app.services.rag import BookParser


def test_split_text_respects_chunk_size():
    parser = BookParser()
    text = ("段落一。这是一段测试文字。" * 20) + "\n\n" + ("段落二。" * 20)
    pieces = parser._split_text(text, chunk_size=80, overlap=10)
    assert len(pieces) > 1
    assert all(len(p) <= 90 for p in pieces)  # 允许在标点处略有伸缩前的上限附近


def test_detect_chapter_chinese():
    assert BookParser._detect_chapter("第一章 条件概率\n正文开始") == "第一章"
    assert BookParser._detect_chapter("Chapter 3 Expectation\nbody") == "Chapter 3"
