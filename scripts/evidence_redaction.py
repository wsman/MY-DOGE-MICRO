from __future__ import annotations

import json
import re
from typing import Any


SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "bearer",
    "client_secret",
    "deepseek_api_key",
    "doge_api_token",
    "id_token",
    "moonshot_api_key",
    "password",
    "refresh_token",
    "secret",
    "token",
}
BEARER_RE = re.compile(
    r"Bearer\s+(?!\[?REDACTED\]?|<redacted>)(?=[A-Za-z0-9._~+/=-]*[._~+/=-])[A-Za-z0-9._~+/=-]{8,}",
    re.IGNORECASE,
)
ASSIGNMENT_RE = re.compile(
    r"\b("
    r"api[_-]?key|password|secret|token|"
    r"access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|"
    r"moonshot_api_key|deepseek_api_key|doge_api_token"
    r")\s*([=:])\s*(['\"]?)([^&\s,'\"}]+)",
    re.IGNORECASE,
)
SK_RE = re.compile(r"\bsk-(?!\[REDACTED\]\b|redacted\b)[A-Za-z0-9._-]{10,}", re.IGNORECASE)


def secret_leak_errors(payload: dict[str, Any], *, subject: str = "completed evidence") -> list[str]:
    errors = _walk(payload, subject=subject, path="$")
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if BEARER_RE.search(rendered):
        errors.append(f"{subject} contains unredacted bearer credential")
    if SK_RE.search(rendered):
        errors.append(f"{subject} contains provider-style API key")
    for match in ASSIGNMENT_RE.finditer(rendered):
        if not _is_redacted_value(match.group(4)):
            errors.append(f"{subject} contains unredacted secret assignment: {match.group(1)}")
    return sorted(set(errors))


def _walk(value: Any, *, subject: str, path: str) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}" if isinstance(key, str) else path
            if isinstance(key, str) and _is_sensitive_key(key):
                if isinstance(item, str) and item.strip() and not _is_redacted_value(item):
                    errors.append(f"{subject} contains unredacted sensitive field: {item_path}")
            errors.extend(_walk(item, subject=subject, path=item_path))
        return errors
    if isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_walk(item, subject=subject, path=f"{path}[{index}]"))
        return errors
    if isinstance(value, str):
        if BEARER_RE.search(value):
            errors.append(f"{subject} contains unredacted bearer credential at {path}")
        if SK_RE.search(value):
            errors.append(f"{subject} contains provider-style API key at {path}")
        for match in ASSIGNMENT_RE.finditer(value):
            if not _is_redacted_value(match.group(4)):
                errors.append(f"{subject} contains unredacted secret assignment at {path}: {match.group(1)}")
    return errors


def _is_sensitive_key(key: str) -> bool:
    return key.lower().replace("-", "_") in SENSITIVE_KEYS


def _is_redacted_value(value: str) -> bool:
    normalized = value.strip().strip("'\"").lower()
    return normalized in {"", "<redacted>", "[redacted]", "redacted", "***"} or "redacted" in normalized
