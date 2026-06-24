import pytest

from doge.core.domain.model_policy import ModelPolicy


def test_model_policy_defaults_and_roundtrip_unknown_fields():
    policy = ModelPolicy.from_dict({"max_tool_rounds": "4", "custom_flag": "kept"})

    assert policy.execution_profile == "financial_research"
    assert policy.max_tool_rounds == 4
    assert policy.to_dict()["custom_flag"] == "kept"


def test_model_policy_strips_identity_snapshot_fields():
    policy = ModelPolicy.from_dict({
        "tenant_id": "tenant-a",
        "user_hash": "user-a",
        "role": "analyst",
        "request_id": "req-1",
        "custom_flag": "kept",
    })

    payload = policy.to_dict()

    assert "tenant_id" not in payload
    assert "user_hash" not in payload
    assert "role" not in payload
    assert "request_id" not in payload
    assert payload["custom_flag"] == "kept"


def test_model_policy_accepts_existing_instance():
    policy = ModelPolicy(execution_profile="quant_code")

    assert ModelPolicy.from_dict(policy) is policy


def test_model_policy_rejects_out_of_range_values():
    with pytest.raises(ValueError, match="max_tool_rounds"):
        ModelPolicy.from_dict({"max_tool_rounds": 0})

    with pytest.raises(ValueError, match="max_tokens"):
        ModelPolicy.from_dict({"max_tokens": 65537})
