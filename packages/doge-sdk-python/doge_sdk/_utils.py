"""Shared SDK transport helpers."""

from __future__ import annotations

import re

import httpx


_BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b("
    r"api[_-]?key|password|secret|token|"
    r"access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|"
    r"moonshot_api_key|deepseek_api_key|doge_api_token"
    r")\s*([=:])\s*(['\"]?)[^&\s,'\"}]+",
    re.IGNORECASE,
)
_SK_PATTERN = re.compile(r"\bsk-[A-Za-z0-9._-]{6,}")


def client_headers(api_token: str | None, request_id: str | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    if request_id:
        headers["X-Request-ID"] = request_id
    return headers


def response_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
        return payload.get("error", {}).get("message") or payload.get("detail") or response.text
    except Exception:
        return response.text


def redact_message(message: str, api_token: str | None) -> str:
    redacted = _BEARER_PATTERN.sub("Bearer [REDACTED]", message)
    redacted = _SECRET_ASSIGNMENT_PATTERN.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", redacted)
    redacted = _SK_PATTERN.sub("sk-[REDACTED]", redacted)
    if api_token:
        redacted = redacted.replace(api_token, "[REDACTED]")
    return redacted
