"""Recursive secret redaction for audit, trace, and debug payloads."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import re
from typing import Any


_SENSITIVE_KEY_PARTS = (
    "api_key",
    "authorization",
    "bearer",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "client_secret",
    "moonshot_api_key",
    "deepseek_api_key",
    "doge_api_token",
)
_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_ASSIGNMENT_RE = re.compile(
    r"\b("
    r"api[_-]?key|password|secret|token|"
    r"access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|"
    r"moonshot_api_key|deepseek_api_key|doge_api_token"
    r")\s*([=:])\s*(['\"]?)[^&\s,'\"}]+",
    re.IGNORECASE,
)
_SK_RE = re.compile(r"\bsk-[A-Za-z0-9._-]{6,}")


def redact_secrets(value: Any, *, replacement: str = "<redacted>") -> Any:
    """Return a copy of ``value`` with credential-shaped data redacted.

    This helper is intentionally small and dependency-free so it can be used by
    API routes, CLI trace output, and audit export code without pulling in an
    infrastructure dependency.
    """

    if is_dataclass(value) and not isinstance(value, type):
        return redact_secrets(asdict(value), replacement=replacement)
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            if isinstance(key, str) and _is_sensitive_key(key):
                redacted[key] = replacement
            else:
                redacted[key] = redact_secrets(item, replacement=replacement)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item, replacement=replacement) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item, replacement=replacement) for item in value)
    if isinstance(value, str):
        return _redact_string(value, replacement=replacement)
    return value


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def _redact_string(value: str, *, replacement: str) -> str:
    redacted = _BEARER_RE.sub("Bearer [REDACTED]", value)
    redacted = _ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}{match.group(2)}{replacement}", redacted)
    redacted = _SK_RE.sub("sk-[REDACTED]", redacted)
    return redacted
