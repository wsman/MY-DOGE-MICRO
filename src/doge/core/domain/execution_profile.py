"""Named execution profiles for Kimi-backed agent runs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionProfile(str, Enum):
    DOCUMENT_EXTRACT = "document_extract"
    VISION_ANALYSIS = "vision_analysis"
    FINANCIAL_RESEARCH = "financial_research"
    QUANT_CODE = "quant_code"
    PYTHON_ANALYSIS = "python_analysis"
    SQL_QUERY = "sql_query"
    BACKTEST = "backtest"
    DATA_PIPELINE = "data_pipeline"
    SCRIPTED_TEST = "scripted_test"
    WEB_RESEARCH = "web_research"
    BATCH_EVAL = "batch_eval"
    AGENT_AUTOMATION = "agent_automation"


@dataclass(frozen=True)
class ExecutionProfileSpec:
    profile: ExecutionProfile
    backend: str
    model_setting: str
    thinking_enabled: bool
    files_purpose: str | None
    web_search_enabled: bool = False
    tool_names: tuple[str, ...] | None = None


class ProfileRegistry:
    """Static profile registry used by routing and policy validation."""

    _SPECS = {
        ExecutionProfile.DOCUMENT_EXTRACT.value: ExecutionProfileSpec(
            profile=ExecutionProfile.DOCUMENT_EXTRACT,
            backend="direct_kimi_api",
            model_setting="general_model",
            thinking_enabled=False,
            files_purpose="file-extract",
        ),
        ExecutionProfile.VISION_ANALYSIS.value: ExecutionProfileSpec(
            profile=ExecutionProfile.VISION_ANALYSIS,
            backend="direct_kimi_api",
            model_setting="general_model",
            thinking_enabled=True,
            files_purpose="image",
        ),
        ExecutionProfile.FINANCIAL_RESEARCH.value: ExecutionProfileSpec(
            profile=ExecutionProfile.FINANCIAL_RESEARCH,
            backend="direct_kimi_api",
            model_setting="general_model",
            thinking_enabled=True,
            files_purpose="file-extract",
        ),
        ExecutionProfile.QUANT_CODE.value: ExecutionProfileSpec(
            profile=ExecutionProfile.QUANT_CODE,
            backend="direct_kimi_api",
            model_setting="code_model",
            thinking_enabled=True,
            files_purpose="file-extract",
            tool_names=("lookup_evidence", "generate_industry_report"),
        ),
        ExecutionProfile.PYTHON_ANALYSIS.value: ExecutionProfileSpec(
            profile=ExecutionProfile.PYTHON_ANALYSIS,
            backend="direct_kimi_api",
            model_setting="code_model",
            thinking_enabled=True,
            files_purpose="file-extract",
            tool_names=("lookup_evidence",),
        ),
        ExecutionProfile.SQL_QUERY.value: ExecutionProfileSpec(
            profile=ExecutionProfile.SQL_QUERY,
            backend="direct_kimi_api",
            model_setting="code_model",
            thinking_enabled=True,
            files_purpose="file-extract",
            tool_names=("lookup_evidence",),
        ),
        ExecutionProfile.BACKTEST.value: ExecutionProfileSpec(
            profile=ExecutionProfile.BACKTEST,
            backend="direct_kimi_api",
            model_setting="code_model",
            thinking_enabled=True,
            files_purpose="file-extract",
            tool_names=("lookup_evidence",),
        ),
        ExecutionProfile.DATA_PIPELINE.value: ExecutionProfileSpec(
            profile=ExecutionProfile.DATA_PIPELINE,
            backend="direct_kimi_api",
            model_setting="code_model",
            thinking_enabled=True,
            files_purpose="file-extract",
            tool_names=("lookup_evidence",),
        ),
        ExecutionProfile.SCRIPTED_TEST.value: ExecutionProfileSpec(
            profile=ExecutionProfile.SCRIPTED_TEST,
            backend="scripted",
            model_setting="general_model",
            thinking_enabled=False,
            files_purpose=None,
        ),
        ExecutionProfile.WEB_RESEARCH.value: ExecutionProfileSpec(
            profile=ExecutionProfile.WEB_RESEARCH,
            backend="direct_kimi_api",
            model_setting="general_model",
            thinking_enabled=True,
            files_purpose="file-extract",
            web_search_enabled=True,
        ),
        ExecutionProfile.BATCH_EVAL.value: ExecutionProfileSpec(
            profile=ExecutionProfile.BATCH_EVAL,
            backend="direct_kimi_api",
            model_setting="general_model",
            thinking_enabled=False,
            files_purpose="batch",
        ),
        ExecutionProfile.AGENT_AUTOMATION.value: ExecutionProfileSpec(
            profile=ExecutionProfile.AGENT_AUTOMATION,
            backend="kimi_agent_sdk",
            model_setting="general_model",
            thinking_enabled=True,
            files_purpose=None,
        ),
    }

    @classmethod
    def get(cls, profile: str | ExecutionProfile | None) -> ExecutionProfileSpec:
        profile_id = (profile.value if isinstance(profile, ExecutionProfile) else profile) or (
            ExecutionProfile.FINANCIAL_RESEARCH.value
        )
        try:
            return cls._SPECS[profile_id]
        except KeyError as exc:
            valid = ", ".join(sorted(cls._SPECS))
            raise ValueError(f"unknown execution_profile {profile_id!r}; expected one of: {valid}") from exc

    @classmethod
    def ids(cls) -> list[str]:
        return sorted(cls._SPECS)
