"""语音服务测试：ASR / TTS / 语音 key 配置（mock dashscope，不碰网络）"""
import base64
import os
import tempfile
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services.voice import QwenASRService, QwenTTSService


@pytest.fixture(autouse=True)
def _dashscope_key(monkeypatch):
    monkeypatch.setattr(settings, "dashscope_api_key", "test-voice-key")


def _asr_response(status_code: int, text: str = ""):
    message = SimpleNamespace(content=[{"text": text}])
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(
        status_code=status_code,
        code="BadRequest" if status_code != 200 else None,
        message="mock error" if status_code != 200 else None,
        output=SimpleNamespace(choices=[choice]),
    )


def test_asr_transcribe_success_and_tmpfile_cleanup(monkeypatch, tmp_path):
    """正常转写：base64 → 临时文件 → 文本，临时文件用完即删"""
    created = []
    real_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        kwargs["dir"] = tmp_path
        fd, path = real_mkstemp(*args, **kwargs)
        created.append(path)
        return fd, path

    monkeypatch.setattr(tempfile, "mkstemp", tracking_mkstemp)

    from dashscope import MultiModalConversation
    monkeypatch.setattr(
        MultiModalConversation, "call",
        staticmethod(lambda **kwargs: _asr_response(200, "这个定理为什么成立")),
    )

    service = QwenASRService()
    import asyncio
    text = asyncio.run(service.transcribe(base64.b64encode(b"RIFF-fake-wav").decode(), "wav"))

    assert text == "这个定理为什么成立"
    assert len(created) == 1
    assert not os.path.exists(created[0])  # 临时文件已清理


def test_asr_transcribe_api_error(monkeypatch):
    from dashscope import MultiModalConversation
    monkeypatch.setattr(
        MultiModalConversation, "call",
        staticmethod(lambda **kwargs: _asr_response(400)),
    )

    service = QwenASRService()
    import asyncio
    with pytest.raises(RuntimeError, match="ASR 错误"):
        asyncio.run(service.transcribe(base64.b64encode(b"fake").decode(), "wav"))


def test_asr_transcribe_empty_audio():
    service = QwenASRService()
    import asyncio
    with pytest.raises(ValueError, match="音频内容为空"):
        asyncio.run(service.transcribe("", "wav"))


def test_asr_requires_key(monkeypatch):
    monkeypatch.setattr(settings, "dashscope_api_key", None)
    with pytest.raises(ValueError, match="DASHSCOPE_API_KEY"):
        QwenASRService()


def test_aliyun_asr_fails_fast(monkeypatch):
    """provider=aliyun：工厂立即报带指引的 ValueError，而非请求期 NotImplementedError"""
    from app.services import voice as voice_service

    monkeypatch.setattr(settings, "asr_provider", "aliyun")
    with pytest.raises(ValueError, match="尚未实现.*qwen"):
        voice_service.get_asr_service()


def test_aliyun_tts_fails_fast(monkeypatch):
    from app.services import voice as voice_service

    monkeypatch.setattr(settings, "tts_provider", "aliyun")
    with pytest.raises(ValueError, match="尚未实现.*qwen"):
        voice_service.get_tts_service()


class _FakeSynthesizer:
    def __init__(self, model, voice):
        self.model = model
        self.voice = voice

    def call(self, text):
        return b"fake-mp3-bytes"


def test_tts_synthesize_success(monkeypatch):
    from dashscope.audio import tts_v2
    monkeypatch.setattr(tts_v2, "SpeechSynthesizer", _FakeSynthesizer)

    service = QwenTTSService()
    import asyncio
    audio_b64 = asyncio.run(service.synthesize("你好", voice=None))

    assert base64.b64decode(audio_b64) == b"fake-mp3-bytes"


def test_tts_synthesize_failure(monkeypatch):
    class _BrokenSynth(_FakeSynthesizer):
        def call(self, text):
            return b""

        def get_response(self):
            return {"code": "InvalidParameter"}

    from dashscope.audio import tts_v2
    monkeypatch.setattr(tts_v2, "SpeechSynthesizer", _BrokenSynth)

    service = QwenTTSService()
    import asyncio
    with pytest.raises(RuntimeError, match="TTS 错误"):
        asyncio.run(service.synthesize("你好"))


def test_tts_empty_text():
    service = QwenTTSService()
    import asyncio
    with pytest.raises(ValueError, match="合成文本为空"):
        asyncio.run(service.synthesize("   "))


def test_config_put_voice_key_keeps_provider(monkeypatch):
    """PUT /config 带 voice_api_key：写 DASHSCOPE_API_KEY，LLM provider 不变"""
    from fastapi.testclient import TestClient

    import app.routers.config as config_router
    from main import app

    written = {}
    monkeypatch.setattr(
        config_router, "update_env_file",
        lambda updates, **kw: written.update(updates),
    )

    old_provider = settings.llm_provider
    old_key = settings.dashscope_api_key
    try:
        client = TestClient(app)
        resp = client.put("/api/config", json={
            "provider": old_provider,
            "voice_api_key": "sk-new-voice-key-1234",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == old_provider          # provider 未被动过
        assert data["voice_configured"] is True
        assert data["voice_api_key_masked"] == "***1234"
        assert written.get("DASHSCOPE_API_KEY") == "sk-new-voice-key-1234"
        assert settings.dashscope_api_key == "sk-new-voice-key-1234"  # 热生效
    finally:
        settings.dashscope_api_key = old_key
