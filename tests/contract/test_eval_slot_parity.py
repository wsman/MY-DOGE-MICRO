"""Eval suite slot consumer parity tests (Sprint 042)."""

from __future__ import annotations

from pathlib import Path

import pytest

from doge.bootstrap.runtime_factories import slots as slots_module
from doge.config import Settings, reset_settings
from doge.config.settings import FeatureConfig
from doge.eval import runner as eval_runner
from doge.eval.suites import EvalSuiteRegistry
from doge.platform.slots import (
    EvalSuiteContribution,
    ISlot,
    SlotConfigurationError,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotProvides,
    SlotRegistry,
    SlotType,
)

_ALL_FEATURE_VARS = [
    "DOGE_FEATURE_RUN_SUMMARY_API",
    "DOGE_FEATURE_PLATFORM_OBJECTS",
    "DOGE_FEATURE_WORKFLOW_TEMPLATES",
    "DOGE_FEATURE_CAPABILITY_REGISTRY",
    "DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER",
    "DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED",
    "DOGE_FEATURE_SLOT_PLATFORM",
    "DOGE_FEATURE_SLOT_GOVERNANCE",
    "DOGE_FEATURE_SLOT_WATCHER",
    "DOGE_FEATURE_SLOT_UI",
    "DOGE_FEATURE_SLOT_ENFORCEMENT",
    "DOGE_FEATURE_SLOT_LOADER",
    "DOGE_FEATURE_SLOT_INSTALL",
]


class _EvalSlot(ISlot):
    def __init__(self, slot_id: str, *, suite_id: str, cases_path: Path) -> None:
        self._slot_id = slot_id
        self._suite_id = suite_id
        self._cases_path = cases_path

    def manifest(self) -> SlotManifest:
        return SlotManifest(
            schema_version=1,
            id=self._slot_id,
            name="Test Eval Slot",
            version="1.0.0",
            type=SlotType.EVAL,
            owner="slot-tests",
            maturity="experimental",
            description="Test eval suite slot.",
            entrypoint="tests.contract.test_eval_slot_parity.EvalSlot",
            provides=SlotProvides(capabilities=("eval.suite",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform",),
        )

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id=self._slot_id,
            eval_suites=(
                EvalSuiteContribution(
                    suite_id=self._suite_id,
                    gold_set_path=str(self._cases_path),
                    execution_profile="test",
                    eval_policy=("offline",),
                ),
            ),
        )


def test_eval_slot_off_returns_no_registry() -> None:
    registry = slots_module.build_slot_aware_eval_suites(
        settings=Settings(features=FeatureConfig(slot_platform=False))
    )

    assert registry is None


def test_builtin_eval_slot_registry_resolves_local_cases() -> None:
    registry = slots_module.build_slot_aware_eval_suites(
        settings=Settings(features=FeatureConfig(slot_platform=True))
    )

    assert isinstance(registry, EvalSuiteRegistry)
    assert "eval.local_cases" in registry.suite_ids
    assert registry.cases_path("eval.local_cases").name == "cases.json"
    assert registry.cases_path("eval.local_cases").exists()


def test_eval_runner_run_suite_uses_slot_contributed_cases(
    monkeypatch,
    tmp_path,
) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text("[]", encoding="utf-8")
    registry = SlotRegistry()
    registry.register(_EvalSlot("eval.custom_slot", suite_id="eval.custom", cases_path=cases))
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()
    calls: list[Path] = []

    def fake_run(cases_path: Path, runtime_factory=None):
        calls.append(cases_path)
        return {"cases_path": str(cases_path), "runtime_factory": runtime_factory}

    monkeypatch.setattr(eval_runner, "run", fake_run)

    result = eval_runner.run_suite("eval.custom")

    assert calls == [cases.resolve()]
    assert result["cases_path"] == str(cases.resolve())


def test_duplicate_eval_suite_contribution_fails_fast(monkeypatch, tmp_path) -> None:
    cases = tmp_path / "cases.json"
    cases.write_text("[]", encoding="utf-8")
    registry = SlotRegistry()
    registry.register(_EvalSlot("eval.one", suite_id="eval.duplicate", cases_path=cases))
    registry.register(_EvalSlot("eval.two", suite_id="eval.duplicate", cases_path=cases))
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)

    with pytest.raises(SlotConfigurationError, match="duplicate eval suite"):
        slots_module.build_slot_aware_eval_suites(
            settings=Settings(features=FeatureConfig(slot_platform=True))
        )


def _strip_feature_env(monkeypatch, keep: set[str] | None = None) -> None:
    keep = keep or set()
    for var in _ALL_FEATURE_VARS:
        if var not in keep:
            monkeypatch.delenv(var, raising=False)
