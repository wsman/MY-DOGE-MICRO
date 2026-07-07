"""Document parser dispatcher tests for Sprint 039."""

from __future__ import annotations

import pytest

from doge.platform.evidence.document_parsers import ParserDispatcher
from doge.platform.slots import (
    DocumentParserContribution,
    SlotConfigurationError,
    SlotContext,
)


class _Parser:
    def __init__(self, name: str) -> None:
        self.name = name

    def parse(self, path, *, max_chars: int = 12000) -> str:
        return f"{self.name}:{path.name}:{max_chars}"


def _context() -> SlotContext:
    return SlotContext(settings=object(), feature_flags={"slot_platform": True})


def test_dispatcher_prefers_exact_suffix_over_wildcard(tmp_path) -> None:
    source = tmp_path / "report.md"
    source.write_text("ignored", encoding="utf-8")
    dispatcher = ParserDispatcher(
        (
            DocumentParserContribution(
                "document.wildcard",
                lambda _context: _Parser("wildcard"),
                ("*",),
                priority=100,
            ),
            DocumentParserContribution(
                "document.markdown",
                lambda _context: _Parser("markdown"),
                (".md",),
                priority=0,
            ),
        ),
        _context(),
    )

    assert dispatcher.parse(source, max_chars=7) == "markdown:report.md:7"


def test_dispatcher_uses_priority_within_same_suffix_rank(tmp_path) -> None:
    source = tmp_path / "report.txt"
    source.write_text("ignored", encoding="utf-8")
    dispatcher = ParserDispatcher(
        (
            DocumentParserContribution(
                "document.low",
                lambda _context: _Parser("low"),
                (".txt",),
                priority=0,
            ),
            DocumentParserContribution(
                "document.high",
                lambda _context: _Parser("high"),
                (".txt",),
                priority=10,
            ),
        ),
        _context(),
    )

    assert dispatcher.parse(source) == "high:report.txt:12000"


def test_dispatcher_rejects_duplicate_parser_ids() -> None:
    with pytest.raises(SlotConfigurationError, match="duplicate document parser"):
        ParserDispatcher(
            (
                DocumentParserContribution("document.dup", lambda _context: _Parser("a"), ("*",)),
                DocumentParserContribution("document.dup", lambda _context: _Parser("b"), ("*",)),
            ),
            _context(),
        )


def test_dispatcher_rejects_unsupported_suffix(tmp_path) -> None:
    source = tmp_path / "report.pdf"
    source.write_bytes(b"%PDF")
    dispatcher = ParserDispatcher(
        (
            DocumentParserContribution(
                "document.text",
                lambda _context: _Parser("text"),
                (".txt",),
            ),
        ),
        _context(),
    )

    with pytest.raises(SlotConfigurationError, match="no document parser supports suffix"):
        dispatcher.parse(source)
