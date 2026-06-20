from doge.infrastructure.documents import FileExtractor, LocalDocumentParser


def test_local_parser_reads_text_file(tmp_path):
    path = tmp_path / "portfolio.csv"
    path.write_text("ticker,weight\nAAPL,0.24\n", encoding="utf-8")

    assert "AAPL" in LocalDocumentParser().parse(path)


def test_file_extractor_returns_document_record(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("# Notes", encoding="utf-8")

    record = FileExtractor().extract(path)

    assert record["document_id"] == "doc-notes"
    assert record["filename"] == "notes.md"
    assert record["content"] == "# Notes"
