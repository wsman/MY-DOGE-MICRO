from pathlib import Path

import doge_sdk
from doge_sdk import Approval, Artifact, DogeEvent, Run, RunEvent, RunListItem


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_run_model_preserves_dict_semantics_with_typed_nested_models():
    payload = {
        "run_id": "run-1",
        "workflow": "earnings_review",
        "question": "Analyze NVDA",
        "session_id": "ses-1",
        "market": "US",
        "language": "en",
        "document_ids": ["doc-1"],
        "portfolio_id": "portfolio-1",
        "model_policy": {"execution_profile": "balanced"},
        "workflow_context": {"scenario": "earnings"},
        "identity_snapshot": {"role": "analyst"},
        "status": "awaiting_approval",
        "events": [
            {
                "event_id": "evt-1",
                "run_id": "run-1",
                "event_type": "approval_requested",
                "payload": {"approval_id": "appr-1"},
                "sequence": 4,
                "schema_version": "1",
                "created_at": "2026-07-06T00:00:00Z",
            }
        ],
        "artifacts": [
            {
                "artifact_id": "art-1",
                "kind": "memo",
                "title": "Memo",
                "content": "Draft",
                "run_id": "run-1",
                "data": {"format": "markdown"},
                "created_at": "2026-07-06T00:00:01Z",
            }
        ],
        "approvals": [
            {
                "approval_id": "appr-1",
                "action": "publish_investment_memo",
                "risk_level": "high",
                "run_id": "run-1",
                "status": "pending",
                "created_at": "2026-07-06T00:00:02Z",
                "resolved_at": None,
                "impact": "Marks memo ready for review.",
            }
        ],
        "cancel_requested_at": None,
        "schema_version": "1",
        "created_at": "2026-07-06T00:00:00Z",
        "updated_at": "2026-07-06T00:00:03Z",
    }

    run = Run(payload)

    assert isinstance(run, dict)
    assert run == payload
    assert run["run_id"] == "run-1"
    assert run.get("status") == "awaiting_approval"
    assert callable(run.get)
    assert callable(run.items)
    assert callable(run.keys)
    assert run.run_id == "run-1"
    assert run.workflow == "earnings_review"
    assert run.question == "Analyze NVDA"
    assert run.session_id == "ses-1"
    assert run.market == "US"
    assert run.language == "en"
    assert run.document_ids == ["doc-1"]
    assert run.portfolio_id == "portfolio-1"
    assert run.model_policy == {"execution_profile": "balanced"}
    assert run.workflow_context == {"scenario": "earnings"}
    assert run.identity_snapshot == {"role": "analyst"}
    assert run.status == "awaiting_approval"
    assert run.cancel_requested_at is None
    assert run.schema_version == "1"
    assert run.created_at == "2026-07-06T00:00:00Z"
    assert run.updated_at == "2026-07-06T00:00:03Z"
    assert isinstance(run["events"][0], RunEvent)
    assert isinstance(run["artifacts"][0], Artifact)
    assert isinstance(run["approvals"][0], Approval)
    assert run.events[0] is run["events"][0]
    assert run.artifacts[0] is run["artifacts"][0]
    assert run.approvals[0] is run["approvals"][0]
    assert run.events[0].event_type == "approval_requested"
    assert run.events[0].payload == {"approval_id": "appr-1"}
    assert run.events[0].sequence == 4
    assert run.artifacts[0].artifact_id == "art-1"
    assert run.artifacts[0].data == {"format": "markdown"}
    assert run.approvals[0].approval_id == "appr-1"
    assert run.approvals[0].status == "pending"
    assert run.approvals[0].why_needed is None
    assert run.approvals[0].impact == "Marks memo ready for review."
    assert run.approvals[0].deny_consequence is None
    assert run.approvals[0].publish_target is None


def test_run_model_does_not_insert_missing_nested_lists():
    run = Run({"run_id": "run-1", "status": "completed"})

    assert run == {"run_id": "run-1", "status": "completed"}
    assert run.events == []
    assert run.artifacts == []
    assert run.approvals == []


def test_run_model_preserves_non_list_nested_payload_values():
    run = Run({"run_id": "run-1", "status": "completed", "approvals": None})

    assert run == {"run_id": "run-1", "status": "completed", "approvals": None}
    assert run.approvals == []


def test_run_list_item_and_event_models_are_dict_compatible():
    row = RunListItem(
        {
            "run_id": "run-1",
            "workflow": "portfolio_risk_review",
            "question": "Analyze portfolio",
            "session_id": None,
            "market": "US",
            "language": "en",
            "portfolio_id": None,
            "status": "completed",
            "event_count": 5,
            "artifact_count": 1,
            "approval_count": 0,
            "created_at": "2026-07-06T00:00:00Z",
            "updated_at": "2026-07-06T00:00:03Z",
        }
    )
    event = RunEvent({"sequence": 2, "event_type": "tool_result"})

    assert row == {
        "run_id": "run-1",
        "workflow": "portfolio_risk_review",
        "question": "Analyze portfolio",
        "session_id": None,
        "market": "US",
        "language": "en",
        "portfolio_id": None,
        "status": "completed",
        "event_count": 5,
        "artifact_count": 1,
        "approval_count": 0,
        "created_at": "2026-07-06T00:00:00Z",
        "updated_at": "2026-07-06T00:00:03Z",
    }
    assert row.workflow == "portfolio_risk_review"
    assert row.event_count == 5
    assert row.artifact_count == 1
    assert row.approval_count == 0
    assert event == {"sequence": 2, "event_type": "tool_result"}
    assert event.sequence == 2
    assert event.event_type == "tool_result"


def test_run_models_are_exported_without_changing_stream_event_type():
    assert doge_sdk.Run is Run
    assert doge_sdk.RunListItem is RunListItem
    assert doge_sdk.Artifact is Artifact
    assert doge_sdk.Approval is Approval
    assert doge_sdk.RunEvent is RunEvent

    event = DogeEvent(id="1", type="run_created", data={"run_id": "run-1"})

    assert doge_sdk.DogeEvent is DogeEvent
    assert not isinstance(event, dict)
    assert event.type == "run_created"


def test_run_models_do_not_add_runtime_modeling_dependencies():
    source = (
        PROJECT_ROOT / "packages" / "doge-sdk-python" / "doge_sdk" / "run_models.py"
    ).read_text(encoding="utf-8")

    assert "pydantic" not in source.lower()
    assert "dataclass" not in source
