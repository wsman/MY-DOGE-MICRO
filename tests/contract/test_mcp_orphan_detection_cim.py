"""Contract tests for MCP orphan-process detection CIM migration (S006-003).

The old ``wmic process where ProcessId={pid} get CommandLine /value`` call is
deprecated on modern Windows. The server now uses PowerShell CIM. This test
verifies the subprocess command shape and fallback behavior without requiring a
real orphan process.
"""
import os
import subprocess as _sp
from unittest.mock import MagicMock

import pytest

from doge.interfaces.mcp import server as srv


class TestMcpOrphanDetectionCim:
    """Verify Windows orphan detection uses CIM and tolerates subprocess failure."""

    @pytest.mark.skipif(not srv._IS_WINDOWS, reason="Windows-only CIM path")
    def test_sync_detect_uses_powershell_cim(self, tmp_path, monkeypatch):
        """The Windows branch must invoke PowerShell Get-CimInstance."""
        pid_file = tmp_path / ".mcp_server.pid"
        # Write a PID that is not the current process so the branch runs.
        other_pid = os.getpid() + 9999
        pid_file.write_text(f"{other_pid}\n", encoding="utf-8")
        monkeypatch.setattr(srv, "PID_FILE", pid_file)

        captured = {}

        def fake_run(args, *, capture_output, text, timeout):
            captured["args"] = args
            mock = MagicMock()
            mock.stdout = "CommandLine : python doge_mcp.py --transport sse\n"
            mock.stderr = ""
            return mock

        monkeypatch.setattr(_sp, "run", fake_run)

        # Should not raise; orphan detection is advisory.
        srv._sync_detect_orphan_processes()

        assert captured["args"][0] == "powershell"
        assert any("Get-CimInstance" in a for a in captured["args"])
        assert any("Win32_Process" in a for a in captured["args"])
        assert f"ProcessId={other_pid}" in "".join(captured["args"])

    @pytest.mark.skipif(not srv._IS_WINDOWS, reason="Windows-only CIM path")
    def test_sync_detect_falls_back_on_subprocess_failure(self, tmp_path, monkeypatch):
        """If PowerShell is missing, the function logs debug and returns."""
        pid_file = tmp_path / ".mcp_server.pid"
        other_pid = os.getpid() + 9999
        pid_file.write_text(f"{other_pid}\n", encoding="utf-8")
        monkeypatch.setattr(srv, "PID_FILE", pid_file)

        def fake_run(*args, **kwargs):
            raise FileNotFoundError("powershell not found")

        monkeypatch.setattr(_sp, "run", fake_run)

        # Advisory only: must not propagate the exception.
        srv._sync_detect_orphan_processes()

    @pytest.mark.skipif(srv._IS_WINDOWS, reason="POSIX path uses /proc directly")
    def test_posix_path_reads_proc_cmdline(self, tmp_path, monkeypatch):
        """Non-Windows path reads /proc/{pid}/cmdline without subprocess."""
        pid_file = tmp_path / ".mcp_server.pid"
        other_pid = os.getpid() + 9999
        pid_file.write_text(f"{other_pid}\n", encoding="utf-8")
        monkeypatch.setattr(srv, "PID_FILE", pid_file)

        class FakePath:
            """Stub that matches the server's Path(f'/proc/{pid}/cmdline') call."""

            def __init__(self, path: str):
                self._path = path

            def read_text(self, *args, **kwargs):  # noqa: ARG002
                assert self._path == f"/proc/{other_pid}/cmdline"
                return "python\x00doge_mcp.py\x00--transport\x00sse\x00"

        original_is_windows = srv._IS_WINDOWS
        srv._IS_WINDOWS = False
        monkeypatch.setattr(srv, "Path", FakePath)
        try:
            srv._sync_detect_orphan_processes()
        finally:
            srv._IS_WINDOWS = original_is_windows
