"""Governance categories for agent-callable tools."""

from __future__ import annotations

from enum import Enum


class ToolCategory(str, Enum):
    READ_ONLY = "read_only"
    ANALYTICAL = "analytical"
    GENERATIVE = "generative"
    HIGH_RISK = "high_risk"
    FORBIDDEN = "forbidden"
