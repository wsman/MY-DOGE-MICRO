from doge.application.use_cases.capability_registry import BuildCapabilityRegistry
from doge.application.capabilities.registry import (
    ApiCapabilityProvider,
    FeatureCapabilityProvider,
    MaturityCapabilityProvider,
    ModelProviderCapabilityProvider,
    ToolRegistryCapabilityProvider,
)
from doge.application.agent.tools import build_default_tool_registry
from doge.application.agent.tool_service import ToolApplicationService
from doge.application.capabilities.executors import SubprocessCodeExecutor
from doge.config import Settings
from doge.config.settings import FEATURE_LIFECYCLES, DeepSeekConfig, FeatureConfig, KimiConfig
from doge.core.domain.tool_policy import ToolCategory


def test_capability_registry_redacts_provider_secrets_and_blocks_production_ready():
    settings = Settings(
        kimi=KimiConfig(api_key="moonshot-secret"),
        deepseek=DeepSeekConfig(api_key="deepseek-secret"),
        features=FeatureConfig(capability_registry=True, run_summary_api=True),
    )

    snapshot = BuildCapabilityRegistry(settings).build()
    text = repr(snapshot)
    capabilities = {item["capability_id"]: item for item in snapshot["capabilities"]}

    assert "moonshot-secret" not in text
    assert "deepseek-secret" not in text
    assert capabilities["provider.kimi"]["status"] == "available"
    assert capabilities["provider.kimi"]["metadata"] == {"configured": True}
    assert capabilities["feature.run_summary_api"]["status"] == "available"
    assert capabilities["feature.run_summary_api"]["metadata"]["lifecycle"]["env_var"] == (
        "DOGE_FEATURE_RUN_SUMMARY_API"
    )
    assert capabilities["maturity.production_ready"]["status"] == "blocked"
    assert capabilities["maturity.stable_declaration"]["status"] == "blocked"
    assert capabilities["feature.python_analysis_enabled"]["status"] == "disabled"
    assert capabilities["feature.python_analysis_enabled"]["risk_level"] == "high"


def test_capability_provider_split_preserves_existing_non_tool_capabilities():
    settings = Settings(features=FeatureConfig(capability_registry=True, run_summary_api=True))
    direct = BuildCapabilityRegistry(settings).build()
    split = BuildCapabilityRegistry(
        settings,
        providers=[
            FeatureCapabilityProvider(settings),
            ModelProviderCapabilityProvider(settings),
            ApiCapabilityProvider(settings),
            MaturityCapabilityProvider(settings.project_root / "docs" / "progress" / "runtime-maturity.yaml"),
        ],
    ).build()

    assert _stable_snapshot(direct) == _stable_snapshot(split)


def test_feature_capabilities_include_lifecycle_metadata():
    snapshot = BuildCapabilityRegistry(Settings()).build()
    capabilities = {item["capability_id"]: item for item in snapshot["capabilities"]}

    expected = {
        "feature.run_summary_api": "run_summary_api",
        "feature.platform_objects": "platform_objects",
        "feature.workflow_templates": "workflow_templates",
        "feature.capability_registry": "capability_registry",
        "feature.python_analysis_enabled": "python_analysis_enabled",
    }
    for capability_id, feature_name in expected.items():
        lifecycle = capabilities[capability_id]["metadata"]["lifecycle"]
        assert lifecycle["env_var"] == FEATURE_LIFECYCLES[feature_name].env_var
        assert lifecycle["current_default"] is False
        assert lifecycle["target_default_on"]
        assert lifecycle["target_removal"]
        assert lifecycle["replacement_behavior"]
        assert lifecycle["regression_commands"]
        assert lifecycle["rollback_criterion"]


def test_python_analysis_feature_requires_enabled_flag_and_executor():
    disabled_executor = FeatureCapabilityProvider(
        Settings(features=FeatureConfig(python_analysis_enabled=True, python_analysis_executor="disabled"))
    ).collect()
    subprocess_executor = FeatureCapabilityProvider(
        Settings(features=FeatureConfig(python_analysis_enabled=True, python_analysis_executor="subprocess"))
    ).collect()

    assert _capability(disabled_executor, "feature.python_analysis_enabled")["status"] == "disabled"
    assert _capability(subprocess_executor, "feature.python_analysis_enabled")["status"] == "available"


def test_tool_capability_provider_matches_default_tool_registry_schemas():
    registry = build_default_tool_registry()
    snapshot = BuildCapabilityRegistry(
        Settings(features=FeatureConfig(capability_registry=True)),
        providers=[ToolRegistryCapabilityProvider(registry)],
    ).build()

    schema_names = {schema["function"]["name"] for schema in registry.schemas}
    tool_caps = {
        item["capability_id"].replace("tool.", ""): item
        for item in snapshot["capabilities"]
        if item["kind"] == "tool"
    }

    assert set(tool_caps) == schema_names
    assert tool_caps["publish_investment_memo"]["requires_approval"] is True
    assert tool_caps["publish_investment_memo"]["risk_level"] == "high"
    assert tool_caps["propose_portfolio_rebalance"]["requires_approval"] is True
    assert tool_caps["run_python_analysis"]["status"] == "disabled"
    assert tool_caps["run_python_analysis"]["requires_approval"] is True
    assert tool_caps["run_python_analysis"]["risk_level"] == "high"
    assert tool_caps["run_python_analysis"]["metadata"]["executor"] == "disabled"
    assert tool_caps["run_python_analysis"]["metadata"]["provider"] == "tool_application_service"
    assert tool_caps["run_python_analysis"]["metadata"]["method_name"] == "run_python_analysis"
    assert tool_caps["stock_overview"]["requires_approval"] is False


def test_python_analysis_capability_becomes_available_with_explicit_executor():
    registry = build_default_tool_registry(service=ToolApplicationService(code_executor=SubprocessCodeExecutor()))
    snapshot = BuildCapabilityRegistry(
        Settings(features=FeatureConfig(capability_registry=True, python_analysis_enabled=True)),
        providers=[ToolRegistryCapabilityProvider(registry)],
    ).build()
    capabilities = {item["capability_id"]: item for item in snapshot["capabilities"]}

    assert capabilities["tool.run_python_analysis"]["status"] == "available"
    assert capabilities["tool.run_python_analysis"]["metadata"]["executor"] == "subprocess"


def test_tool_capability_provider_uses_registry_entitlement_redaction():
    registry = build_default_tool_registry(entitlement_checker=_OnlyReadOnlyEntitlements())
    snapshot = BuildCapabilityRegistry(
        Settings(features=FeatureConfig(capability_registry=True)),
        providers=[ToolRegistryCapabilityProvider(registry)],
    ).build(context=object())
    capability_ids = {item["capability_id"] for item in snapshot["capabilities"]}

    assert "tool.stock_overview" in capability_ids
    assert "tool.portfolio_risk" not in capability_ids
    assert "tool.publish_investment_memo" not in capability_ids


def _stable_snapshot(snapshot):
    return [
        {
            key: value
            for key, value in item.items()
            if key not in {"generated_at", "snapshot_id"}
        }
        for item in snapshot["capabilities"]
    ]


def _capability(capabilities, capability_id):
    return next(item for item in capabilities if item["capability_id"] == capability_id)


class _OnlyReadOnlyEntitlements:
    def can_execute(self, context, tool_name, category):
        return category == ToolCategory.READ_ONLY

    def requires_approval(self, context, tool_name, category):
        return category == ToolCategory.HIGH_RISK

    def redact_schema(self, context, schema, category):
        if not self.can_execute(context, schema.get("function", {}).get("name", ""), category):
            return None
        return schema
