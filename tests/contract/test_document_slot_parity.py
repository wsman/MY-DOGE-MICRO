"""Document slot consumer parity tests (Sprint 039)."""

from __future__ import annotations

import pytest

from doge.application.services.page_extraction_service import PageExtractionService
from doge.bootstrap.gateway_factories import documents as document_factories
from doge.bootstrap.runtime_factories import slots as slots_module
from doge.config import reset_settings
from doge.core.domain.document_models import Document, DocumentStatus
from doge.infrastructure.documents.local_parser import LocalDocumentParser
from doge.platform.evidence.document_parsers import ParserDispatcher
from doge.platform.slots import (
    DocumentParserContribution,
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


class _RuntimeContainer:
    def build_agent_evidence_repository(self):
        return None


class _Parser:
    def __init__(self, text: str = "custom parser") -> None:
        self._text = text

    def parse(self, path, *, max_chars: int = 12000) -> str:
        return self._text[:max_chars]


class _DocumentParserSlot(ISlot):
    def __init__(
        self,
        slot_id: str,
        *,
        parser_id: str,
        suffixes: tuple[str, ...] = ("*",),
        priority: int = 0,
        parser=None,
    ) -> None:
        self._slot_id = slot_id
        self._parser_id = parser_id
        self._suffixes = suffixes
        self._priority = priority
        self._parser = parser or _Parser()

    def manifest(self) -> SlotManifest:
        return SlotManifest(
            schema_version=1,
            id=self._slot_id,
            name="Test Document Parser Slot",
            version="1.0.0",
            type=SlotType.DOCUMENT,
            owner="slot-tests",
            maturity="experimental",
            description="Test document parser slot.",
            entrypoint="tests.contract.test_document_slot_parity.DocumentParserSlot",
            provides=SlotProvides(capabilities=("document.parse",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform",),
        )

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id=self._slot_id,
            document_parsers=(
                DocumentParserContribution(
                    parser_id=self._parser_id,
                    factory=lambda _context: self._parser,
                    supported_suffixes=self._suffixes,
                    priority=self._priority,
                ),
            ),
        )


def _strip_feature_env(monkeypatch, keep: set[str] | None = None) -> None:
    keep = keep or set()
    for var in _ALL_FEATURE_VARS:
        if var not in keep:
            monkeypatch.delenv(var, raising=False)


def test_document_slot_off_returns_no_parser(monkeypatch) -> None:
    _strip_feature_env(monkeypatch)
    reset_settings()

    assert slots_module.build_slot_aware_document_parser() is None


def test_default_document_slot_matches_local_parser_for_text_and_binary(monkeypatch, tmp_path) -> None:
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()
    text = tmp_path / "memo.txt"
    text.write_text("alpha beta", encoding="utf-8")
    binary = tmp_path / "report.pdf"
    binary.write_bytes(b"%PDF fake")
    parser = slots_module.build_slot_aware_document_parser()
    legacy = LocalDocumentParser()

    assert isinstance(parser, ParserDispatcher)
    assert parser.parse(text) == legacy.parse(text)
    assert parser.parse(binary) == legacy.parse(binary)


def test_gateway_page_extraction_factory_uses_document_slot_parser(monkeypatch, tmp_path) -> None:
    registry = SlotRegistry()
    registry.register(
        _DocumentParserSlot(
            "document.custom",
            parser_id="document.custom",
            suffixes=(".txt",),
            parser=_Parser("slot extracted"),
        )
    )
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()
    source = tmp_path / "memo.txt"
    source.write_text("legacy text", encoding="utf-8")
    document = Document.create(
        document_id="doc-slot",
        original_filename="memo.txt",
        storage_path=str(source),
        parsing_status=DocumentStatus.UPLOADED,
    )
    service = document_factories.build_page_extraction_service(lambda: _RuntimeContainer())

    result = service.extract(document)

    assert result.errors == []
    assert result.pages[0].text == "slot extracted"


def test_gateway_page_extraction_factory_preserves_legacy_parser_when_slot_platform_off(
    monkeypatch,
    tmp_path,
) -> None:
    _strip_feature_env(monkeypatch)
    reset_settings()
    source = tmp_path / "memo.txt"
    source.write_text("legacy text", encoding="utf-8")
    document = Document.create(
        document_id="doc-legacy",
        original_filename="memo.txt",
        storage_path=str(source),
        parsing_status=DocumentStatus.UPLOADED,
    )
    service = document_factories.build_page_extraction_service(lambda: _RuntimeContainer())
    legacy = PageExtractionService(parser=LocalDocumentParser())

    assert service.extract(document).pages[0].text == legacy.extract(document).pages[0].text


def test_duplicate_document_parser_contribution_fails_fast(monkeypatch) -> None:
    registry = SlotRegistry()
    registry.register(_DocumentParserSlot("document.one", parser_id="document.duplicate"))
    registry.register(_DocumentParserSlot("document.two", parser_id="document.duplicate"))
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()

    with pytest.raises(SlotConfigurationError, match="duplicate document parser"):
        slots_module.build_slot_aware_document_parser()
