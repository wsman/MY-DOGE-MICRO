import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "doged_enterprise_static_auth_smoke.py"


def test_doged_enterprise_static_auth_smoke_help_lists_runtime_options():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        check=True,
        text=True,
    )

    assert "--output-dir" in result.stdout
    assert "--timeout-seconds" in result.stdout
