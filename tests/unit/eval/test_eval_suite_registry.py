"""Eval suite registry tests for Sprint 042."""

from __future__ import annotations

import pytest

from doge.eval.suites import EvalSuiteRegistry
from doge.platform.slots import EvalSuiteContribution, SlotConfigurationError, SlotContext


def test_eval_suite_registry_resolves_cases_path(tmp_path) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text("[]", encoding="utf-8")
    registry = EvalSuiteRegistry(
        (
            EvalSuiteContribution(
                suite_id="eval.custom",
                gold_set_path="cases.json",
                execution_profile="test",
                eval_policy=("offline",),
            ),
        ),
        _context(),
        root=tmp_path,
    )

    assert registry.suite_ids == ("eval.custom",)
    assert registry.cases_path("eval.custom") == cases.resolve()
    assert registry.suite_for("eval.custom").execution_profile == "test"
    assert registry.suite_for("eval.custom").eval_policy == ("offline",)


def test_eval_suite_registry_rejects_duplicate_suite_ids(tmp_path) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text("[]", encoding="utf-8")

    with pytest.raises(SlotConfigurationError, match="duplicate eval suite"):
        EvalSuiteRegistry(
            (
                EvalSuiteContribution("eval.duplicate", "cases.json"),
                EvalSuiteContribution("eval.duplicate", "cases.json"),
            ),
            _context(),
            root=tmp_path,
        )


def test_eval_suite_registry_rejects_missing_cases_path(tmp_path) -> None:
    with pytest.raises(SlotConfigurationError, match="cases path not found"):
        EvalSuiteRegistry(
            (EvalSuiteContribution("eval.missing", "missing.json"),),
            _context(),
            root=tmp_path,
        )


def test_eval_suite_registry_rejects_unknown_suite(tmp_path) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text("[]", encoding="utf-8")
    registry = EvalSuiteRegistry(
        (EvalSuiteContribution("eval.custom", "cases.json"),),
        _context(),
        root=tmp_path,
    )

    with pytest.raises(SlotConfigurationError, match="unknown eval suite"):
        registry.cases_path("eval.nope")


def _context() -> SlotContext:
    return SlotContext(settings=object(), feature_flags={"slot_platform": True})
