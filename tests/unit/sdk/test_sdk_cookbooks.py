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


def test_sdk_cookbook_scaffold_uses_real_environment_names():
    env_example = PROJECT_ROOT / "examples" / ".env.example"
    readme = PROJECT_ROOT / "examples" / "README.md"
    py_makefile = PROJECT_ROOT / "examples" / "python" / "Makefile"
    ts_package = PROJECT_ROOT / "examples" / "typescript" / "package.json"
    ts_config = PROJECT_ROOT / "examples" / "typescript" / "tsconfig.json"

    for path in (env_example, readme, py_makefile, ts_package, ts_config):
        assert path.exists(), f"{path} should exist"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in (
        env_example,
        readme,
        py_makefile,
        ts_package,
        ts_config,
    ))
    assert "DOGE_DAEMON_URL" in combined
    assert "DOGE_API_TOKEN" in combined
    assert "DOGE_SAMPLE_DOC" in combined
    assert "DOGE_SAMPLE_DOC=../../README.md" in combined
    assert "set -a" in combined
    assert ". examples/.env" in combined
    assert "local `.env`" not in combined
    assert "py -3 -m pip install -e packages/doge-sdk-python" in combined
    assert "DOGE_BASE_URL" not in combined
    assert "sk-" not in combined
    assert "file:../../packages/doge-sdk-typescript" in combined
    assert '"@types/node"' in combined
    for target in ("run-01", "run-02", "run-03", "run-04"):
        assert target in combined


def test_upload_cookbooks_resolve_sample_doc_from_script_location():
    python_upload = PROJECT_ROOT / "examples" / "python" / "02_upload_and_run.py"
    typescript_upload = PROJECT_ROOT / "examples" / "typescript" / "02_upload_and_run.ts"

    python_text = python_upload.read_text(encoding="utf-8")
    typescript_text = typescript_upload.read_text(encoding="utf-8")

    assert 'parents[2] / "README.md"' in python_text
    assert "sample_doc_path()" in python_text
    assert "../../README.md" in typescript_text
    assert "fileURLToPath(import.meta.url)" in typescript_text
