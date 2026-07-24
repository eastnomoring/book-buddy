"""配置持久化：读写 .env 并热更新内存中的 settings"""
import re
from pathlib import Path
from typing import Dict, Optional

from app.config import settings

ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


def update_env_file(updates: Dict[str, str], path: Path = ENV_PATH) -> None:
    """更新 .env 中的指定 key（不存在则追加，文件不存在则创建）"""
    lines = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    seen = set()
    out = []
    for line in lines:
        match = re.match(r"\s*#?\s*([A-Z_]+)=", line)
        if match and match.group(1) in updates:
            key = match.group(1)
            if key not in seen:
                out.append(f"{key}={updates[key]}")
                seen.add(key)
            continue
        out.append(line)

    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def mask_key(key: Optional[str]) -> str:
    """key 掩码：前 3 位 + *** + 后 4 位"""
    if not key:
        return ""
    if len(key) <= 7:
        return "***"
    return f"{key[:3]}***{key[-4:]}"


def apply_to_settings(updates: Dict[str, str]) -> None:
    """把 .env 风格的更新热应用到 settings 单例"""
    mapping = {
        "LLM_PROVIDER": "llm_provider",
        "OPENAI_API_KEY": "openai_api_key",
        "OPENAI_BASE_URL": "openai_base_url",
        "OPENAI_MODEL": "openai_model",
        "DASHSCOPE_API_KEY": "dashscope_api_key",
        "LLM_MODEL": "llm_model",
    }
    for env_key, attr in mapping.items():
        if env_key in updates:
            setattr(settings, attr, updates[env_key])

    # 嵌入函数持有旧 key/base_url，置为未初始化以便下次惰性重建
    from app.services.rag import rag_service
    rag_service.vector_store._initialized = False
