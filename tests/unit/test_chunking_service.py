from doge.application.services.page_extraction_service import ChunkingService
from doge.core.domain.page_models import DocumentPage


def test_chunking_service_creates_stable_offsets_and_ids():
    page = DocumentPage.create(
        document_id="doc-1",
        page_number=2,
        text="Revenue grew 10%. " * 20,
        source_hash="hash-1",
    )
    service = ChunkingService(chunk_size=80, overlap=10)

    first = service.chunk_page(page)
    second = service.chunk_page(page)

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert first[0].page_number == 2
    assert first[0].start_char == 0
    assert first[0].end_char <= 80
    assert all(chunk.source_hash == "hash-1" for chunk in first)


def test_chunking_service_ignores_blank_page_text():
    page = DocumentPage.create(document_id="doc-1", page_number=1, text="  ")

    assert ChunkingService().chunk_page(page) == []
