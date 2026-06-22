import json
from pathlib import Path


def test_financial_provider_fixture_contract_samples_include_required_fields():
    path = Path(__file__).resolve().parents[2] / "fixtures" / "financial_connectors" / "provider_fixture_contract.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["status"] == "contract_only"
    allowed_statuses = set(payload["allowed_provider_statuses"])
    for connector, spec in payload["connectors"].items():
        sample = spec["sample"]
        missing = [field for field in spec["required_fields"] if field not in sample]
        assert missing == [], f"{connector} fixture sample is missing {missing}"
        assert sample["license_scope"] == "test"
        assert sample["provider_status"] in allowed_statuses


def test_financial_provider_fixture_samples_cover_safe_success_and_failure_modes():
    root = Path(__file__).resolve().parents[2] / "fixtures" / "financial_connectors"
    contract = json.loads((root / "provider_fixture_contract.json").read_text(encoding="utf-8"))
    samples = json.loads((root / "provider_fixture_samples.json").read_text(encoding="utf-8"))

    assert samples["status"] == "synthetic_safe_samples"
    assert samples["license_scope"] == "test_synthetic"
    assert samples["repository_storage"] == "approved_synthetic_only"
    required_case_types = {"ok", "stale_data", "provider_unavailable", "entitlement_denied", "malformed"}
    allowed_statuses = set(contract["allowed_provider_statuses"])
    for connector, spec in contract["connectors"].items():
        connector_samples = samples["connectors"][connector]["samples"]
        by_case_type = {sample["case_type"]: sample for sample in connector_samples}
        assert set(by_case_type) == required_case_types
        for case_type, sample in by_case_type.items():
            if case_type == "malformed":
                assert "payload" in sample
                assert sample["expected_error"].startswith("missing required")
                missing = [field for field in spec["required_fields"] if field not in sample["payload"]]
                assert missing, f"{connector} malformed fixture should omit at least one required field"
                continue
            missing = [field for field in spec["required_fields"] if field not in sample]
            assert missing == [], f"{connector} {case_type} fixture is missing {missing}"
            assert sample["license_scope"] == "test_synthetic"
            assert sample["provider_status"] in allowed_statuses
            assert sample["provider_status"] == case_type
