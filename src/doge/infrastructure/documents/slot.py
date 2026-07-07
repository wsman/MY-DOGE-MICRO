"""Built-in document parser slot for local deterministic parsing."""

from __future__ import annotations

from doge.infrastructure.documents.local_parser import LocalDocumentParser
from doge.platform.slots import (
    SCHEMA_VERSION,
    DocumentParserContribution,
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

_TEXT_SUFFIXES = tuple(sorted(LocalDocumentParser.TEXT_SUFFIXES))

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="document.local_parser",
    name="Local Document Parser",
    version="1.0.0",
    type=SlotType.DOCUMENT,
    owner="knowledge-evidence",
    maturity="experimental",
    description=(
        "Contributes the deterministic local document parser used by file "
        "upload and page extraction services."
    ),
    entrypoint="doge.infrastructure.documents.slot.LocalDocumentParserSlot",
    provides=SlotProvides(
        capabilities=("document.parse", "document.local_parser"),
        metadata={
            "supported_suffixes": ("*",),
            "text_suffixes": _TEXT_SUFFIXES,
            "fallback": "binary_metadata_snippet",
        },
    ),
    permissions=SlotPermissions(filesystem="read", risk_level="low"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class LocalDocumentParserSlot(ISlot):
    """Built-in document slot wrapping ``LocalDocumentParser``."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id="document.local_parser",
            document_parsers=(
                DocumentParserContribution(
                    parser_id="document.local_parser",
                    factory=_parser_factory,
                    supported_suffixes=("*",),
                    mime_types=(
                        "text/plain",
                        "text/markdown",
                        "text/csv",
                        "application/json",
                    ),
                    priority=0,
                ),
            ),
        )


def _parser_factory(context: SlotContext) -> LocalDocumentParser:
    return LocalDocumentParser()
