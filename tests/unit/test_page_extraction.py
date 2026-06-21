import struct

from doge.application.services.page_extraction_service import PageExtractionService
from doge.core.domain.document_models import Document, DocumentStatus
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository


def test_page_extraction_splits_pdf_like_content_and_persists_chunks(tmp_path):
    db = tmp_path / "agent_state.db"
    repository = SQLiteEvidenceRepository(db)
    document = Document.create(
        document_id="doc-pdf",
        original_filename="report.pdf",
        file_hash="hash-pdf",
        parsing_status=DocumentStatus.PARSED,
        content="Page one revenue.\fPage two margin.",
    )

    result = PageExtractionService(evidence_repository=repository).extract(document)

    assert [page.page_number for page in result.pages] == [1, 2]
    assert len(result.chunks) == 2
    assert repository.list_pages("doc-pdf")[1].text == "Page two margin."
    assert repository.list_chunks(["doc-pdf"], limit=10)[0].source_hash == "hash-pdf"


def test_page_extraction_records_png_metadata(tmp_path):
    image = tmp_path / "chart.png"
    image.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + struct.pack(">II", 640, 360)
        + b"\x08\x02\x00\x00\x00"
    )
    document = Document.create(
        document_id="doc-img",
        original_filename="chart.png",
        file_hash="hash-img",
        mime_type="image/png",
        size_bytes=image.stat().st_size,
        storage_path=str(image),
        parsing_status=DocumentStatus.PARSED,
    )

    result = PageExtractionService().extract(document)

    assert result.errors == []
    assert result.pages[0].image_metadata["width"] == 640
    assert result.pages[0].image_metadata["height"] == 360
    assert result.chunks[0].text.startswith("[image document: chart.png")


def test_page_extraction_captures_parser_errors(tmp_path):
    class FailingParser:
        def parse(self, path, *, max_chars=12000):
            raise RuntimeError("cannot parse")

    source = tmp_path / "broken.pdf"
    source.write_bytes(b"%PDF")
    document = Document.create(
        document_id="doc-broken",
        original_filename="broken.pdf",
        storage_path=str(source),
        parsing_status=DocumentStatus.UPLOADED,
    )

    result = PageExtractionService(parser=FailingParser()).extract(document)

    assert result.chunks == []
    assert result.errors == ["RuntimeError: cannot parse"]
    assert result.pages[0].parser_error == "RuntimeError: cannot parse"
