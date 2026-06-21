import pytest

from doge.core.domain.execution_profile import ExecutionProfile, ProfileRegistry


def test_profile_registry_returns_default_financial_research():
    spec = ProfileRegistry.get(None)

    assert spec.profile == ExecutionProfile.FINANCIAL_RESEARCH
    assert spec.backend == "direct_kimi_api"
    assert spec.thinking_enabled is True


def test_profile_registry_defines_quant_code_as_thinking_code_model():
    spec = ProfileRegistry.get("quant_code")

    assert spec.profile == ExecutionProfile.QUANT_CODE
    assert spec.model_setting == "code_model"
    assert spec.thinking_enabled is True


def test_profile_registry_defines_web_research_search_stage():
    spec = ProfileRegistry.get("web_research")

    assert spec.profile == ExecutionProfile.WEB_RESEARCH
    assert spec.web_search_enabled is True
    assert spec.thinking_enabled is True


def test_profile_registry_rejects_unknown_profile():
    with pytest.raises(ValueError, match="unknown execution_profile"):
        ProfileRegistry.get("unknown")
