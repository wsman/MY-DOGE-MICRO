"""Typed policy for one agent model run."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from doge.core.domain.enterprise_context import IDENTITY_SNAPSHOT_KEYS


@dataclass(frozen=True)
class ModelPolicy:
    """Validated, JSON-friendly model policy.

    Unknown fields are preserved so older/newer records can round-trip through
    repositories without losing operator-provided metadata.
    """

    execution_profile: str = "financial_research"
    max_tool_rounds: int = 8
    max_tokens: int = 16384
    max_completion_tokens: int | None = None
    stream: bool = False
    tool_timeout_seconds: float | None = None
    thinking_enabled: bool | None = None
    web_search_enabled: bool | None = None
    model_family: str | None = None
    response_format: str | dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    prompt_cache_key: str | None = None
    run_budget_usd: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: "ModelPolicy | Mapping[str, Any] | None") -> "ModelPolicy":
        if isinstance(data, cls):
            return data
        payload = dict(data or {})
        known = {
            "execution_profile",
            "max_tool_rounds",
            "max_tokens",
            "max_completion_tokens",
            "stream",
            "tool_timeout_seconds",
            "thinking_enabled",
            "web_search_enabled",
            "model_family",
            "response_format",
            "response_schema",
            "prompt_cache_key",
            "run_budget_usd",
        }
        extra = {
            key: value
            for key, value in payload.items()
            if key not in known and key not in IDENTITY_SNAPSHOT_KEYS
        }
        policy = cls(
            execution_profile=str(payload.get("execution_profile") or cls.execution_profile),
            max_tool_rounds=_coerce_int(payload.get("max_tool_rounds"), cls.max_tool_rounds),
            max_tokens=_coerce_int(payload.get("max_tokens"), cls.max_tokens),
            max_completion_tokens=_coerce_optional_int(payload.get("max_completion_tokens")),
            stream=bool(payload.get("stream", cls.stream)),
            tool_timeout_seconds=_coerce_optional_float(payload.get("tool_timeout_seconds")),
            thinking_enabled=_coerce_optional_bool(payload.get("thinking_enabled")),
            web_search_enabled=_coerce_optional_bool(payload.get("web_search_enabled")),
            model_family=_coerce_optional_str(payload.get("model_family")),
            response_format=payload.get("response_format"),
            response_schema=payload.get("response_schema") if isinstance(payload.get("response_schema"), dict) else None,
            prompt_cache_key=_coerce_optional_str(payload.get("prompt_cache_key")),
            run_budget_usd=_coerce_optional_float(payload.get("run_budget_usd")),
            extra=extra,
        )
        policy.validate()
        return policy

    def to_dict(self) -> dict[str, Any]:
        data = dict(self.extra)
        data.update({
            "execution_profile": self.execution_profile,
            "max_tool_rounds": self.max_tool_rounds,
            "max_tokens": self.max_tokens,
            "max_completion_tokens": self.max_completion_tokens,
            "stream": self.stream,
            "tool_timeout_seconds": self.tool_timeout_seconds,
            "thinking_enabled": self.thinking_enabled,
            "web_search_enabled": self.web_search_enabled,
            "model_family": self.model_family,
            "response_format": self.response_format,
            "response_schema": self.response_schema,
            "prompt_cache_key": self.prompt_cache_key,
            "run_budget_usd": self.run_budget_usd,
        })
        return {key: value for key, value in data.items() if value is not None}

    def validate(self) -> None:
        if not 1 <= self.max_tool_rounds <= 32:
            raise ValueError("max_tool_rounds must be between 1 and 32")
        if not 1 <= self.max_tokens <= 65536:
            raise ValueError("max_tokens must be between 1 and 65536")
        if self.max_completion_tokens is not None and not 1 <= self.max_completion_tokens <= 65536:
            raise ValueError("max_completion_tokens must be between 1 and 65536")
        if self.model_family is not None and self.model_family not in {"k2.6", "k2.7-code", "scripted"}:
            raise ValueError("model_family must be one of: k2.6, k2.7-code, scripted")
        if self.run_budget_usd is not None and self.run_budget_usd < 0:
            raise ValueError("run_budget_usd must be non-negative")

    def with_defaults(self, *, web_search_enabled: bool | None = None) -> "ModelPolicy":
        return ModelPolicy.from_dict({
            **self.to_dict(),
            "web_search_enabled": (
                self.web_search_enabled if self.web_search_enabled is not None else web_search_enabled
            ),
        })


def _coerce_int(value: Any, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _coerce_optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _coerce_optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _coerce_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on", "enabled"}:
            return True
        if lowered in {"false", "0", "no", "off", "disabled"}:
            return False
    return bool(value)
