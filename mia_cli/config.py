from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    tomllib = None  # type: ignore


CONFIG_DIR = Path.home() / ".mia"
CONFIG_PATH = CONFIG_DIR / "config.toml"


class ApiKeys(BaseModel):
    gemini: Optional[str] = None
    openai: Optional[str] = None
    anthropic: Optional[str] = None
    openrouter: Optional[str] = None
    ollama: Optional[str] = None  # typically not a key, but endpoint token if needed


class MiaConfig(BaseModel):
    llm_provider: str = Field(default="gemini")
    api_keys: ApiKeys = Field(default_factory=ApiKeys)


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> MiaConfig:
    if not CONFIG_PATH.exists():
        return MiaConfig()
    if tomllib is None:
        # Fallback: minimal manual parse for very simple defaults
        return MiaConfig()
    data = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    # Coerce nested structure safely
    api_keys_data: Dict[str, Optional[str]] = data.get("api_keys", {}) if isinstance(data, dict) else {}
    return MiaConfig(
        llm_provider=data.get("llm_provider", "gemini"),
        api_keys=ApiKeys(**api_keys_data),
    )


def save_config(cfg: MiaConfig) -> None:
    ensure_config_dir()
    # Minimal TOML writer to avoid extra deps
    lines = [
        f"llm_provider = \"{cfg.llm_provider}\"",
        "",
        "[api_keys]",
        f"gemini = \"{cfg.api_keys.gemini or ''}\"",
        f"openai = \"{cfg.api_keys.openai or ''}\"",
        f"anthropic = \"{cfg.api_keys.anthropic or ''}\"",
        f"openrouter = \"{cfg.api_keys.openrouter or ''}\"",
        f"ollama = \"{cfg.api_keys.ollama or ''}\"",
        "",
    ]
    CONFIG_PATH.write_text("\n".join(lines), encoding="utf-8")