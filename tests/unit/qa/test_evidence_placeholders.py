from scripts.evidence_placeholders import placeholder_errors


def test_placeholder_errors_reject_common_operator_template_tokens():
    payload = {
        "approved_at": "YYYY-MM-DDTHH:MM:SSZ",
        "operator": {"initials": "<initials>"},
        "issue_refs": ["S017-003-TEMPLATE"],
        "environment": {"browser": "TEMPLATE_BROWSER"},
        "command": "$createdAt $analystInitials",
    }

    errors = placeholder_errors(payload)

    assert "completed evidence contains unresolved placeholder: <initials>" in errors
    assert "completed evidence contains unresolved placeholder: YYYY-MM-DDTHH:MM:SSZ" in errors
    assert "completed evidence contains unresolved placeholder: S017-003-TEMPLATE" in errors
    assert "completed evidence contains unresolved placeholder: TEMPLATE_BROWSER" in errors
    assert "completed evidence contains unresolved placeholder: $createdAt" in errors
    assert "completed evidence contains unresolved placeholder: $analystInitials" in errors


def test_placeholder_errors_accept_realistic_completed_values():
    payload = {
        "approved_at": "2026-06-22T09:00:00Z",
        "operator": {"initials": "QA"},
        "issue_refs": ["BUG-123"],
        "environment": {"browser": "Chrome"},
        "evidence_ref": "operator-secure-store://redacted/run-123",
    }

    assert placeholder_errors(payload) == []
