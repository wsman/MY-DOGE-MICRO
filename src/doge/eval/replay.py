"""Replay helpers for persisted evaluation observations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_observations(path: Path | str) -> dict[str, dict[str, Any]]:
    """Load an observation mapping from a JSON benchmark artifact."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    observations = data.get("observations", data)
    if not isinstance(observations, dict):
        raise ValueError("observation artifact must contain a mapping")
    return {str(key): dict(value) for key, value in observations.items()}


def save_replay(path: Path | str, payload: dict[str, Any]) -> None:
    """Write a deterministic replay artifact."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


__all__ = ["load_observations", "save_replay"]
