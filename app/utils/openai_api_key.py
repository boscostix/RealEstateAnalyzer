"""Helpers for resolving the OpenAI API key from env vars or a local secrets file."""

from __future__ import annotations

import os
from pathlib import Path

OPENAI_API_KEY_FILE_ENV = "OPENAI_API_KEY_FILE"
DEFAULT_OPENAI_API_KEY_FILE = "secrets/openai_api_key.txt"


def resolve_openai_api_key() -> str | None:
    """Return the configured OpenAI API key from env or a fallback file."""

    env_value = os.getenv("OPENAI_API_KEY")
    if env_value:
        return env_value

    file_path = os.getenv(OPENAI_API_KEY_FILE_ENV, DEFAULT_OPENAI_API_KEY_FILE)
    path = Path(file_path)
    if not path.is_file():
        return None

    value = path.read_text(encoding="utf-8").strip()
    return value or None


def ensure_openai_api_key_env() -> str | None:
    """Populate `OPENAI_API_KEY` from the fallback file when needed."""

    value = resolve_openai_api_key()
    if value and not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = value
    return value
