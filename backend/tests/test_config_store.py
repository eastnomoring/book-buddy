"""config_store 单元测试（不碰网络）"""
import pytest

from app.services.config_store import mask_key, update_env_file


def test_update_env_file_creates_when_missing(tmp_path):
    path = tmp_path / ".env"
    update_env_file({"OPENAI_API_KEY": "k1", "LLM_PROVIDER": "openai"}, path)
    content = path.read_text()
    assert "OPENAI_API_KEY=k1" in content
    assert "LLM_PROVIDER=openai" in content


def test_update_env_file_updates_existing(tmp_path):
    path = tmp_path / ".env"
    path.write_text("OPENAI_API_KEY=old\nOPENAI_MODEL=glm-4v\n")
    update_env_file({"OPENAI_API_KEY": "new"}, path)
    content = path.read_text()
    assert "OPENAI_API_KEY=new" in content
    assert "old" not in content
    assert "OPENAI_MODEL=glm-4v" in content  # 未涉及的行保留


def test_update_env_file_uncomments_and_dedupes(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# OPENAI_API_KEY=placeholder\nOPENAI_API_KEY=a\nOPENAI_API_KEY=b\n")
    update_env_file({"OPENAI_API_KEY": "final"}, path)
    lines = [l for l in path.read_text().splitlines() if "OPENAI_API_KEY" in l]
    assert lines == ["OPENAI_API_KEY=final"]


@pytest.mark.parametrize("key,expected", [
    (None, ""),
    ("", ""),
    ("1234", "***"),          # 恰好 4 位 → 完全隐藏
    ("12345", "***2345"),     # 5 位 → 露后 4 位
    ("short", "***hort"),     # 5 位 → 露后 4 位
    ("a93e39215af84554b98e7c44c4679b61.uWJhKNGiTbTaskP4", "***skP4"),
])
def test_mask_key(key, expected):
    assert mask_key(key) == expected
