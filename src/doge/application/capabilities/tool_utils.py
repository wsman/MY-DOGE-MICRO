"""Shared helpers for deterministic tool execution providers."""

from __future__ import annotations

import re
from typing import Any, Callable


ServiceFactory = Callable[[], Any]


def claim_matches_rows(claim: str, rows: list[dict[str, Any]]) -> bool:
    numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", claim)]
    if not numbers:
        return False
    numeric_values: list[float] = []
    for row in rows:
        for value in row.values():
            if isinstance(value, (int, float)):
                numeric_values.append(float(value))
    return any(
        abs(claimed - actual) <= max(0.01, abs(actual) * 0.001)
        for claimed in numbers
        for actual in numeric_values
    )


def claim_matches_evidence(claim: str, evidence: list[dict[str, Any]]) -> bool:
    numbers = re.findall(r"\d+(?:\.\d+)?", claim)
    texts = " ".join(str(item.get("text", "")) for item in evidence).lower()
    if numbers:
        return any(number in texts for number in numbers)
    claim_terms = {term for term in re.findall(r"[\w\u4e00-\u9fff]+", claim.lower()) if len(term) > 3}
    if not claim_terms:
        return False
    evidence_terms = set(re.findall(r"[\w\u4e00-\u9fff]+", texts))
    return bool(claim_terms & evidence_terms)


def document_scope_from_context(context: Any) -> list[str] | None:
    if context is None:
        return None
    acl = sorted(getattr(context, "document_acl", frozenset()) or [])
    if is_restricted_context(context):
        return acl
    return acl or None


def filter_results_for_context(results: list[dict[str, Any]], context: Any) -> list[dict[str, Any]]:
    if not is_restricted_context(context):
        return results
    allowed = set(getattr(context, "document_acl", frozenset()) or [])
    if not allowed:
        return []
    return [
        item
        for item in results
        if item.get("document_id") in allowed
    ]


def is_restricted_context(context: Any) -> bool:
    if context is None:
        return False
    return getattr(context, "tenant_id", "local") != "local"


def num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def looks_mutating_sql(sql: str) -> bool:
    stripped = sql.strip().lower()
    if not (stripped.startswith("select") or stripped.startswith("with")):
        return True
    return bool(re.search(r"\b(insert|update|delete|drop|alter|create|attach|copy|pragma)\b", stripped))


def unsafe_python(code: str) -> bool:
    lowered = code.lower()
    blocked = (
        "import os",
        "import subprocess",
        "import socket",
        "from os",
        "from subprocess",
        "open(",
        "__",
        "eval(",
        "exec(",
    )
    return any(token in lowered for token in blocked)


def resolve(factory: ServiceFactory | None, dependency_name: str) -> Any:
    if factory is None:
        raise RuntimeError(f"Tool dependency not configured: {dependency_name}")
    return factory()
