"""Built-in document slot tests for Sprint 039."""

from __future__ import annotations

from doge.infrastructure.documents.local_parser import LocalDocumentParser
from doge.infrastructure.documents.slot import LocalDocumentParserSlot
from doge.platform.slots import SlotContext, SlotType


def test_local_document_parser_slot_manifest() -> None:
    manifest = LocalDocumentParserSlot().manifest()

    assert manifest.id == "document.local_parser"
    assert manifest.type is SlotType.DOCUMENT
    assert manifest.owner == "knowledge-evidence"
    assert manifest.feature_flags == ("slot_platform",)
    assert manifest.provides.capabilities == ("document.parse", "document.local_parser")
    assert manifest.provides.metadata["supported_suffixes"] == ("*",)
    assert manifest.permissions.filesystem == "read"
    assert manifest.permissions.risk_level == "low"


def test_local_document_parser_slot_contributes_parser() -> None:
    context = SlotContext(settings=object(), feature_flags={"slot_platform": True})

    contribution = LocalDocumentParserSlot().resolve(context)

    assert contribution.slot_id == "document.local_parser"
    assert len(contribution.document_parsers) == 1
    parser = contribution.document_parsers[0]
    assert parser.parser_id == "document.local_parser"
    assert parser.supported_suffixes == ("*",)
    assert isinstance(parser.factory(context), LocalDocumentParser)
