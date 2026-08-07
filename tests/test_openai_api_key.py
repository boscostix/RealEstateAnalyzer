"""Tests for resolving the OpenAI API key from env vars and local files."""

from __future__ import annotations

import os
from pathlib import Path

from pytest import MonkeyPatch

from app.utils.openai_api_key import ensure_openai_api_key_env, resolve_openai_api_key


def test_resolve_openai_api_key_reads_fallback_file(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    key_file = tmp_path / "openai_api_key.txt"
    key_file.write_text("sk-test-123\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(key_file))

    assert resolve_openai_api_key() == "sk-test-123"


def test_ensure_openai_api_key_env_populates_missing_env(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    key_file = tmp_path / "openai_api_key.txt"
    key_file.write_text("sk-test-456\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(key_file))

    assert ensure_openai_api_key_env() == "sk-test-456"
    assert os.environ["OPENAI_API_KEY"] == "sk-test-456"
