"""Sanitization helpers for committee model inputs."""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel

from app.agent_research.sanitization import sanitize_untrusted_text

T = TypeVar("T")

SECRET_REPLACEMENT = "[redacted secret]"

_HTML_TAG_PATTERN = re.compile(r"(?is)<[^>]+>")
_SECRET_PATTERN = re.compile(
    r"(?is)\b(api[_ -]?key|access[_ -]?token|bearer token|password|secret)\b"
    r"([^\n]{0,80})"
)
_SECRET_KEY_NAMES = {
    "api_key",
    "apikey",
    "token",
    "access_token",
    "password",
    "secret",
    "authorization",
    "cookie",
}


def sanitize_committee_text(value: str, *, max_length: int = 1200) -> tuple[str, list[str]]:
    """Strip raw HTML, redact secrets, and filter prompt-injection-like text."""

    warnings: list[str] = []
    without_html = _HTML_TAG_PATTERN.sub(" ", value)
    if without_html != value:
        warnings.append("raw_html_removed")
    redacted = _SECRET_PATTERN.sub(lambda _: SECRET_REPLACEMENT, without_html)
    if redacted != without_html:
        warnings.append("secret_redacted")
    sanitized, changed = sanitize_untrusted_text(redacted, max_length=max_length)
    if changed:
        warnings.append("prompt_injection_filtered")
    return sanitized, list(dict.fromkeys(warnings))


def sanitize_committee_value[T](value: T) -> tuple[T, list[str]]:
    """Recursively sanitize a model/dict/list used for committee model input."""

    warnings: list[str] = []

    def _sanitize(node: object, *, parent_key: str | None = None) -> object:
        if isinstance(node, str):
            sanitized, local_warnings = sanitize_committee_text(node)
            warnings.extend(local_warnings)
            return sanitized
        if isinstance(node, list):
            return [_sanitize(item) for item in node]
        if isinstance(node, tuple):
            return tuple(_sanitize(item) for item in node)
        if isinstance(node, dict):
            sanitized_dict: dict[object, object] = {}
            for key, item in node.items():
                normalized_key = str(key).lower()
                if normalized_key in _SECRET_KEY_NAMES:
                    sanitized_dict[key] = SECRET_REPLACEMENT
                    warnings.append("secret_redacted")
                    continue
                sanitized_dict[key] = _sanitize(item, parent_key=normalized_key)
            return sanitized_dict
        return node

    if isinstance(value, BaseModel):
        sanitized_dump = _sanitize(value.model_dump(mode="python"))
        sanitized = value.__class__.model_validate(sanitized_dump)
        return sanitized, list(dict.fromkeys(warnings))

    return _sanitize(value), list(dict.fromkeys(warnings))  # type: ignore[return-value]


def serialize_committee_model_input(value: BaseModel) -> str:
    """Serialize a committee model-input payload in a stable sorted-key form."""

    return json.dumps(
        value.model_dump(mode="json", exclude_none=False),
        sort_keys=True,
        separators=(",", ":"),
    )
