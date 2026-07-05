"""Sprint E tool-provider ownership checks."""

from __future__ import annotations

import inspect

from doge.application.agent import tool_service
from doge.application.agent.tool_service import ToolApplicationService


def test_tool_providers_are_importable_from_owning_contexts() -> None:
    from doge.platform.governance.tools import ComplianceToolProvider, PublishingToolProvider
    from doge.products.market.tools import MarketToolProvider
    from doge.products.portfolio.tools import PortfolioToolProvider
    from doge.products.quant.tools import QuantToolProvider
    from doge.products.research.tools import FundamentalToolProvider, ResearchToolProvider

    assert MarketToolProvider.__name__ == "MarketToolProvider"
    assert ResearchToolProvider.__name__ == "ResearchToolProvider"
    assert FundamentalToolProvider.__name__ == "FundamentalToolProvider"
    assert PortfolioToolProvider.__name__ == "PortfolioToolProvider"
    assert QuantToolProvider.__name__ == "QuantToolProvider"
    assert ComplianceToolProvider.__name__ == "ComplianceToolProvider"
    assert PublishingToolProvider.__name__ == "PublishingToolProvider"


def test_tool_application_service_exposes_generic_executor() -> None:
    service = ToolApplicationService()

    result = service.execute("request_approval", "publish", "high")

    base = {key: result[key] for key in ("approval_required", "action", "risk_level")}
    assert base == {
        "approval_required": True,
        "action": "publish",
        "risk_level": "high",
    }
    assert result["why_needed"]
    assert result["impact"]
    assert result["deny_consequence"]
    assert result["publish_target"]


def test_tool_application_service_compatibility_delegate_list_is_frozen() -> None:
    expected = set(tool_service.COMPATIBILITY_TOOL_METHODS)
    public_methods = {
        name
        for name, member in inspect.getmembers(ToolApplicationService, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    allowed_non_tool_methods = {
        "execute",
        "execution_provider_method_names",
        "python_analysis_capability_status",
        "tool_descriptors",
    }

    assert expected == set(ToolApplicationService().execution_provider_method_names())
    assert public_methods - allowed_non_tool_methods == expected
