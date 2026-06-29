"""Web gate for ADR-0024 legacy `/api/*` compatibility usage."""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WEB_SRC = PROJECT_ROOT / "web" / "src"

ALLOWED_LEGACY_API_STRINGS = {
    "/api",
    "/api/scan/${market}",
    "/api/scan/cn",
    "/api/scan/us",
    "/api/scan/servers",
    "/api/scan/servers/test",
}


def test_web_legacy_api_strings_are_named_compatibility_exceptions() -> None:
    found: dict[str, list[str]] = {}
    for path in WEB_SRC.rglob("*"):
        if path.suffix not in {".ts", ".vue"}:
            continue
        source = _strip_comments(path.read_text(encoding="utf-8"))
        for value in _string_literals(source):
            if value.startswith("/api"):
                found.setdefault(value, []).append(str(path.relative_to(PROJECT_ROOT)))

    unexpected = {value: paths for value, paths in found.items() if value not in ALLOWED_LEGACY_API_STRINGS}

    assert unexpected == {}


def test_legacy_api_allowlist_is_scanner_and_axios_base_only() -> None:
    assert ALLOWED_LEGACY_API_STRINGS == {
        "/api",
        "/api/scan/${market}",
        "/api/scan/cn",
        "/api/scan/us",
        "/api/scan/servers",
        "/api/scan/servers/test",
    }


def _strip_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//.*", "", source)


def _string_literals(source: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r"""(?P<quote>['"`])(?P<value>.*?)(?P=quote)""", source, flags=re.DOTALL):
        value = match.group("value")
        if value.startswith("/api"):
            values.append(value)
    return values
