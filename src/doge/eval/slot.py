"""Built-in eval suite slots."""

from __future__ import annotations

from doge.platform.slots import (
    SCHEMA_VERSION,
    EvalSuiteContribution,
    ISlot,
    SlotCompatibility,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotPermissions,
    SlotProvides,
    SlotType,
)

_LOCAL_CASES_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="eval.local_cases",
    name="Local Eval Cases",
    version="1.0.0",
    type=SlotType.EVAL,
    owner="governance-evaluation",
    maturity="experimental",
    description="Contributes the deterministic local eval cases used by the offline eval runner.",
    entrypoint="doge.eval.slot.LocalEvalCasesSlot",
    provides=SlotProvides(
        capabilities=("eval.suite", "eval.local_cases"),
        metadata={
            "suite_id": "eval.local_cases",
            "gold_set_path": "tests/eval/cases.json",
        },
    ),
    permissions=SlotPermissions(filesystem="read", risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class LocalEvalCasesSlot(ISlot):
    """Built-in eval slot wrapping the deterministic local cases file."""

    def manifest(self) -> SlotManifest:
        return _LOCAL_CASES_MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id="eval.local_cases",
            eval_suites=(
                EvalSuiteContribution(
                    suite_id="eval.local_cases",
                    gold_set_path="tests/eval/cases.json",
                    execution_profile="local_alpha",
                    eval_policy=("offline", "deterministic"),
                ),
            ),
        )
