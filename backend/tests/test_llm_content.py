"""LLM content 提取与基础行为测试"""
import pytest

from app.services.llm import extract_text_content


@pytest.mark.parametrize(
    "content,expected",
    [
        (None, ""),
        ("hello", "hello"),
        ([{"text": "你好"}, {"text": "世界"}], "你好世界"),
        ({"text": "only"}, "only"),
        ([{"image": "x"}, {"text": "caption"}], "caption"),
    ],
)
def test_extract_text_content(content, expected):
    assert extract_text_content(content) == expected
