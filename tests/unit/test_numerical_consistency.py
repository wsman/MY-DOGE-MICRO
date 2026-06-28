from doge.application.services.numerical_consistency_service import NumericalConsistencyService
from doge.core.domain.agent_models import AgentEvent, EventType


def test_numerical_consistency_scores_matching_numbers():
    service = NumericalConsistencyService()

    assert service.score_numbers([100.0, 50.0], [100.2, 10.0]) == 0.5


def test_numerical_consistency_returns_none_without_comparable_numbers():
    assert NumericalConsistencyService().score_numbers([], [1.0]) is None


def test_numerical_consistency_scores_single_claim_numbers():
    service = NumericalConsistencyService()

    assert service.score_claim_numbers("Revenue grew 12%.", ["Revenue grew 12.1%."]) == 1.0


def test_numerical_consistency_ignores_boolean_tool_flags():
    service = NumericalConsistencyService()
    events = [
        AgentEvent(
            event_id="evt-1",
            run_id="run-1",
            event_type=EventType.TOOL_RESULT,
            payload={"result": {"ok": True}},
        )
    ]

    assert service.score_artifact("Question 1. Review the memo.", events) is None
