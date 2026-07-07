"""Built-in eval slot tests for Sprint 042."""

from __future__ import annotations

from doge.eval.slot import LocalEvalCasesSlot
from doge.platform.slots import SlotContext, SlotType


def test_local_eval_cases_slot_manifest() -> None:
    manifest = LocalEvalCasesSlot().manifest()

    assert manifest.id == "eval.local_cases"
    assert manifest.type is SlotType.EVAL
    assert manifest.owner == "governance-evaluation"
    assert manifest.feature_flags == ("slot_platform",)
    assert manifest.provides.capabilities == ("eval.suite", "eval.local_cases")
    assert manifest.provides.metadata["suite_id"] == "eval.local_cases"
    assert manifest.provides.metadata["gold_set_path"] == "tests/eval/cases.json"
    assert manifest.permissions.filesystem == "read"
    assert manifest.permissions.risk_level == "low"


def test_local_eval_cases_slot_contributes_suite() -> None:
    context = SlotContext(settings=object(), feature_flags={"slot_platform": True})

    contribution = LocalEvalCasesSlot().resolve(context)

    assert contribution.slot_id == "eval.local_cases"
    assert len(contribution.eval_suites) == 1
    suite = contribution.eval_suites[0]
    assert suite.suite_id == "eval.local_cases"
    assert suite.gold_set_path == "tests/eval/cases.json"
    assert suite.execution_profile == "local_alpha"
    assert suite.eval_policy == ("offline", "deterministic")
