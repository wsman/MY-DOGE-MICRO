"""Eval suite selection for slot-contributed offline eval cases."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from doge.platform.slots import (
    EvalSuiteContribution,
    SlotConfigurationError,
    SlotContext,
)


@dataclass(frozen=True)
class EvalSuiteRecord:
    suite_id: str
    gold_set_path: Path
    execution_profile: str | None
    eval_policy: tuple[str, ...]


class EvalSuiteRegistry:
    """Registry of slot-contributed offline eval suites."""

    def __init__(
        self,
        eval_suites: Iterable[EvalSuiteContribution],
        context: SlotContext,
        *,
        root: Path | None = None,
    ) -> None:
        del context
        base = root or Path.cwd()
        records: list[EvalSuiteRecord] = []
        seen: set[str] = set()
        for contribution in eval_suites:
            if contribution.suite_id in seen:
                raise SlotConfigurationError(
                    f"duplicate eval suite contribution: {contribution.suite_id}"
                )
            seen.add(contribution.suite_id)
            path = _resolve_path(base, contribution.gold_set_path)
            if not path.exists():
                raise SlotConfigurationError(
                    f"eval suite {contribution.suite_id} cases path not found: {path}"
                )
            records.append(
                EvalSuiteRecord(
                    suite_id=contribution.suite_id,
                    gold_set_path=path,
                    execution_profile=contribution.execution_profile,
                    eval_policy=tuple(contribution.eval_policy),
                )
            )
        if not records:
            raise ValueError("EvalSuiteRegistry requires at least one suite")
        self._records = tuple(records)

    @property
    def suite_ids(self) -> tuple[str, ...]:
        return tuple(record.suite_id for record in self._records)

    def suite_for(self, suite_id: str | None = None) -> EvalSuiteRecord:
        resolved_id = suite_id or self._records[0].suite_id
        for record in self._records:
            if record.suite_id == resolved_id:
                return record
        raise SlotConfigurationError(f"unknown eval suite: {resolved_id}")

    def cases_path(self, suite_id: str | None = None) -> Path:
        return self.suite_for(suite_id).gold_set_path


def _resolve_path(base: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = base / path
    return path.resolve()
