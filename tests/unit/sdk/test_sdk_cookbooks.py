import py_compile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_python_sdk_cookbooks_are_compilable():
    files = sorted((PROJECT_ROOT / "examples" / "python").glob("*.py"))

    assert [path.name for path in files] == [
        "01_create_session.py",
        "02_upload_and_run.py",
        "03_stream_and_approve.py",
        "04_error_handling.py",
    ]
    for path in files:
        py_compile.compile(str(path), doraise=True)


def test_typescript_sdk_cookbooks_cover_primary_flows_without_literal_tokens():
    files = sorted((PROJECT_ROOT / "examples" / "typescript").glob("*.ts"))

    assert [path.name for path in files] == [
        "01_create_session.ts",
        "02_upload_and_run.ts",
        "03_stream_and_approve.ts",
        "04_error_handling.ts",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    assert "new DogeClient" in combined
    assert ".sessions.create" in combined
    assert ".documents.upload" in combined
    assert ".runs.stream" in combined
    assert ".runs.resume" in combined
    assert "sk-" not in combined
    assert "DOGE_API_TOKEN" in combined
