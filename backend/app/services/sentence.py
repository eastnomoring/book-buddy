"""把 LLM 增量文本切成完整句子（与 packages/core SentenceStreamer 对齐）。"""
import re
from typing import List

_SENTENCE_END = re.compile(r"[。！？!？；;\n]")


def spoken_text(sentence: str) -> str:
    """把 markdown/公式转成适合朗读的纯文本。"""
    text = sentence
    text = re.sub(r"\$\$[\s\S]+?\$\$", "，公式，", text)
    text = re.sub(r"\$[^\n$]+?\$", "公式", text)
    text = re.sub(r"```[\s\S]*?```", "，代码片段，", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "，图片，", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*`#>]", "", text)
    return text.strip()


class SentenceSplitter:
    """增量切句；feed 返回新完成的句子列表，flush 冲刷残余。"""

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, delta: str) -> List[str]:
        self._buffer += delta
        out: List[str] = []
        while True:
            m = _SENTENCE_END.search(self._buffer)
            if not m:
                break
            sentence = self._buffer[: m.end()].strip()
            self._buffer = self._buffer[m.end() :]
            if sentence:
                out.append(sentence)
        return out

    def flush(self) -> List[str]:
        rest = self._buffer.strip()
        self._buffer = ""
        return [rest] if rest else []
