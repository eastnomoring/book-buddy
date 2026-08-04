"""Z4: 按句切分 + 服务端 TTS 叠加流"""
import asyncio
from typing import AsyncIterator

from app.services.sentence import SentenceSplitter, spoken_text
from app.services.stream_tts import iter_with_sentence_tts


def test_sentence_splitter_basic():
    s = SentenceSplitter()
    assert s.feed("你好。世界") == ["你好。"]
    assert s.feed("！还有一句\n") == ["世界！", "还有一句"]
    assert s.flush() == []


def test_sentence_splitter_flush_rest():
    s = SentenceSplitter()
    assert s.feed("没有句号") == []
    assert s.flush() == ["没有句号"]


def test_spoken_text_strips_formula():
    assert "公式" in spoken_text("期望 $E[X]$ 很大")
    assert "```" not in spoken_text("见 ```py\nprint(1)\n```")


class _FakeTTS:
    def __init__(self):
        self.calls: list[str] = []

    async def synthesize(self, text, voice=None):
        self.calls.append(text)
        await asyncio.sleep(0.01)
        return "YXVkaW8="


async def _events() -> AsyncIterator[dict]:
    yield {"delta": "第一句。", "done": False}
    yield {"delta": "第二句！", "done": False}
    yield {"delta": "", "done": True}


def test_iter_with_sentence_tts_emits_audio():
    async def run():
        tts = _FakeTTS()
        out = []
        async for ev in iter_with_sentence_tts(_events(), tts):
            out.append(ev)

        deltas = [e for e in out if e.get("delta")]
        audios = [e for e in out if e.get("type") == "audio"]
        dones = [e for e in out if e.get("done")]

        assert len(deltas) >= 2
        assert len(audios) == 2
        assert audios[0]["mimeType"] == "audio/mpeg"
        assert audios[0]["base64"] == "YXVkaW8="
        assert tts.calls == ["第一句。", "第二句！"]
        assert dones and dones[-1]["done"] is True

    asyncio.run(run())


def test_iter_without_tts_passthrough():
    async def run():
        out = []
        async for ev in iter_with_sentence_tts(_events(), None):
            out.append(ev)
        assert all(e.get("type") != "audio" for e in out)
        assert out[-1]["done"] is True

    asyncio.run(run())


def test_tts_overlaps_with_later_deltas():
    """首句 TTS 与后续 LLM delta 重叠：首句 audio 可在 done 之前到达。"""

    class SlowTTS(_FakeTTS):
        async def synthesize(self, text, voice=None):
            self.calls.append(text)
            await asyncio.sleep(0.05)
            return "YXVkaW8="

    async def slow_events() -> AsyncIterator[dict]:
        yield {"delta": "第一句。", "done": False}
        await asyncio.sleep(0.08)  # 模拟后续吐字，期间首句 TTS 应已完成
        yield {"delta": "第二句！", "done": False}
        yield {"delta": "", "done": True}

    async def run():
        tts = SlowTTS()
        saw_audio_before_done = False
        async for ev in iter_with_sentence_tts(slow_events(), tts):
            if ev.get("type") == "audio":
                saw_audio_before_done = True
            if ev.get("done"):
                assert saw_audio_before_done, "首句 audio 应在 done 前到达（重叠）"
                return

    asyncio.run(run())
