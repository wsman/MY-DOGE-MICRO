from pathlib import Path


def test_scan_router_has_no_legacy_micro_imports():
    text = Path("src/doge/interfaces/api/routers/scan.py").read_text(encoding="utf-8")

    forbidden = [
        "src.micro",
        "from micro",
        "import micro",
        "tdx_downloader",
    ]
    assert not any(pattern in text for pattern in forbidden)
