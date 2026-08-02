"""Prompt-injection protections for untrusted research text."""

from __future__ import annotations

import re
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")

UNTRUSTED_TEXT_REPLACEMENT = "[filtered untrusted text removed]"

_PROMPT_INJECTION_PATTERNS = (
    re.compile(
        r"(?is)\b(ignore|disregard|override)\b.{0,80}\b(previous|prior|above)\b.{0,80}"
        r"\b(instruction|instructions|direction|directions|prompt|message|messages)\b"
    ),
    re.compile(r"(?is)\b(system prompt|developer message|hidden instructions?)\b"),
    re.compile(r"(?is)\b(reveal|print|show)\b.{0,80}\b(api key|secret|password|token)\b"),
    re.compile(r"(?is)<script\b|</script>|javascript:"),
)


def sanitize_untrusted_text(value: str, *, max_length: int = 1000) -> tuple[str, bool]:
    """Normalize or replace untrusted text that looks like prompt injection."""

    collapsed = " ".join(value.replace("\x00", " ").split())
    trimmed = collapsed[:max_length]
    for pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(trimmed):
            return UNTRUSTED_TEXT_REPLACEMENT, True
    return trimmed, False


def sanitize_for_agent[T](value: T) -> tuple[T, list[str]]:
    """Recursively sanitize strings inside a value returned to an agent."""

    warnings: list[str] = []

    def _sanitize(node: object) -> object:
        if isinstance(node, str):
            sanitized, changed = sanitize_untrusted_text(node)
            if changed:
                warnings.append("prompt_injection_filtered")
            return sanitized
        if isinstance(node, list):
            return [_sanitize(item) for item in node]
        if isinstance(node, tuple):
            return tuple(_sanitize(item) for item in node)
        if isinstance(node, dict):
            return {key: _sanitize(item) for key, item in node.items()}
        return node

    if isinstance(value, BaseModel):
        sanitized_dump = _sanitize(value.model_dump(mode="python"))
        sanitized = value.__class__.model_validate(sanitized_dump)
        return sanitized, list(dict.fromkeys(warnings))

    return _sanitize(value), list(dict.fromkeys(warnings))  # type: ignore[return-value]
