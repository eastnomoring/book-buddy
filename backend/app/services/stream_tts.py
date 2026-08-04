"""Z4：在文本 SSE 流上叠加按句 TTS，音频事件与文本并行下发。

设计目标（相对「前端每句再 HTTP 调 /voice/synthesize」）：
- 去掉每句一次 RTT
- LLM 继续吐字的同时后台合成已完成的句子
- 协议：{"type":"audio","id":"a1","mimeType":"audio/mpeg","base64":"...","text":"..."}
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

from app.services.sentence import SentenceSplitter, spoken_text
from app.services.voice import TTSService


async def iter_with_sentence_tts(
    text_events: AsyncIterator[dict],
    tts: Optional[TTSService],
) -> AsyncIterator[dict]:
    """消费上游事件（delta / tool_* / done / error），在有 tts 时插入 audio 事件。"""
    if tts is None:
        async for event in text_events:
            yield event
        return

    splitter = SentenceSplitter()
    pending: list[asyncio.Task] = []
    next_id = 0

    async def _synth(sentence: str, audio_id: str) -> dict:
        text = spoken_text(sentence)
        if not text:
            return {}
        audio = await tts.synthesize(text)
        return {
            "type": "audio",
            "id": audio_id,
            "mimeType": "audio/mpeg",
            "base64": audio,
            "text": text,
        }

    def _schedule(sentence: str) -> None:
        nonlocal next_id
        next_id += 1
        pending.append(asyncio.create_task(_synth(sentence, f"a{next_id}")))

    def _take_finished() -> list[dict]:
        finished: list[dict] = []
        still: list[asyncio.Task] = []
        for task in pending:
            if task.done():
                if task.cancelled():
                    continue
                exc = task.exception()
                if exc is not None:
                    # 单句失败不中断整条流
                    continue
                ev = task.result()
                if ev:
                    finished.append(ev)
            else:
                still.append(task)
        pending.clear()
        pending.extend(still)
        return finished

    try:
        async for event in text_events:
            if event.get("error"):
                for task in pending:
                    task.cancel()
                yield event
                return

            etype = event.get("type")
            if etype in ("tool_call", "tool_result"):
                yield event
                for audio_ev in _take_finished():
                    yield audio_ev
                continue

            delta = event.get("delta")
            if delta:
                yield event
                for sentence in splitter.feed(delta):
                    _schedule(sentence)
                for audio_ev in _take_finished():
                    yield audio_ev
                continue

            if event.get("done"):
                for sentence in splitter.flush():
                    _schedule(sentence)
                for task in pending:
                    try:
                        ev = await task
                    except Exception:
                        continue
                    if ev:
                        yield ev
                pending.clear()
                yield event
                return

            yield event
            for audio_ev in _take_finished():
                yield audio_ev
    finally:
        for task in pending:
            if not task.done():
                task.cancel()
