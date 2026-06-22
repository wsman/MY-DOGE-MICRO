from __future__ import annotations

import json
import re
from typing import Any


PLACEHOLDER_PATTERNS = [
    re.compile(r"<[^>\n]+>"),
    re.compile(r"\bYYYY-MM-DD(?:THH:MM:SSZ)?\b"),
    re.compile(r"\$createdAt\b"),
    re.compile(r"\$analystInitials\b"),
    re.compile(r"\b[A-Z0-9-]+-TEMPLATE\b"),
    re.compile(r"\bTEMPLATE_[A-Z0-9_]+\b"),
]


def placeholder_errors(payload: dict[str, Any], *, subject: str = "completed evidence") -> list[str]:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    matches = sorted({match.group(0) for pattern in PLACEHOLDER_PATTERNS for match in pattern.finditer(text)})
    return [f"{subject} contains unresolved placeholder: {match}" for match in matches]
