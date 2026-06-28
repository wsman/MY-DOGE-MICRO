"""Runtime-backed agent use-case factories."""

from __future__ import annotations

from doge.application.use_cases.industry_analyzer import IndustryAnalyzerAgentUseCase
from doge.application.use_cases.macro_strategist import MacroStrategistAgentUseCase


def build_macro_strategist_agent_use_case(persisted_runtime_fn, runtime=None):
    if runtime is None:
        runtime = persisted_runtime_fn()
    return MacroStrategistAgentUseCase(runtime)


def build_industry_analyzer_agent_use_case(persisted_runtime_fn, runtime=None):
    if runtime is None:
        runtime = persisted_runtime_fn()
    return IndustryAnalyzerAgentUseCase(runtime)
