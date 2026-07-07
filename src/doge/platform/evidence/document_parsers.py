"""Document parser dispatching for slot-contributed parsers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from doge.platform.slots import (
    DocumentParserContribution,
    SlotConfigurationError,
    SlotContext,
)


@dataclass(frozen=True)
class _ParserEntry:
    parser_id: str
    parser: object
    supported_suffixes: tuple[str, ...]
    priority: int


class ParserDispatcher:
    """Dispatch document parsing to slot-contributed parser instances."""

    def __init__(
        self,
        parser_contributions: Iterable[DocumentParserContribution],
        context: SlotContext,
    ) -> None:
        entries: list[_ParserEntry] = []
        seen: set[str] = set()
        for contribution in parser_contributions:
            if contribution.parser_id in seen:
                raise SlotConfigurationError(
                    f"duplicate document parser contribution: {contribution.parser_id}"
                )
            seen.add(contribution.parser_id)
            parser = contribution.factory(context)
            if parser is None:
                raise SlotConfigurationError(
                    f"document parser {contribution.parser_id} returned no parser"
                )
            entries.append(
                _ParserEntry(
                    parser_id=contribution.parser_id,
                    parser=parser,
                    supported_suffixes=_normalize_suffixes(contribution.supported_suffixes),
                    priority=contribution.priority,
                )
            )
        if not entries:
            raise ValueError("ParserDispatcher requires at least one parser")
        self._entries = tuple(entries)

    @property
    def parser_ids(self) -> tuple[str, ...]:
        return tuple(entry.parser_id for entry in self._entries)

    def parse(self, path: str | Path, *, max_chars: int = 12000) -> str:
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        entry = self._select_parser(suffix)
        parser = entry.parser
        parse = getattr(parser, "parse", None)
        if parse is None:
            raise SlotConfigurationError(
                f"document parser {entry.parser_id} does not expose parse()"
            )
        return parse(file_path, max_chars=max_chars)

    def _select_parser(self, suffix: str) -> _ParserEntry:
        ranked: list[tuple[int, int, str, _ParserEntry]] = []
        for entry in self._entries:
            rank = _suffix_rank(entry.supported_suffixes, suffix)
            if rank <= 0:
                continue
            ranked.append((rank, entry.priority, entry.parser_id, entry))
        if not ranked:
            raise SlotConfigurationError(
                f"no document parser supports suffix: {suffix or '<none>'}"
            )
        ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return ranked[0][3]


def _normalize_suffixes(suffixes: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for suffix in suffixes:
        value = suffix.strip().lower()
        if not value:
            continue
        if value != "*" and not value.startswith("."):
            value = f".{value}"
        normalized.append(value)
    if not normalized:
        raise SlotConfigurationError("document parser must declare supported_suffixes")
    return tuple(normalized)


def _suffix_rank(suffixes: tuple[str, ...], suffix: str) -> int:
    if suffix and suffix in suffixes:
        return 2
    if "*" in suffixes:
        return 1
    return 0
