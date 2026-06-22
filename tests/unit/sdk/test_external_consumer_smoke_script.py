import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "sdk_external_consumer_smoke.py"


def test_sdk_external_consumer_smoke_help_lists_package_options():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=True,
        text=True,
    )

    assert "--workspace" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--python-executable" in result.stdout
    assert "--node-path" in result.stdout
