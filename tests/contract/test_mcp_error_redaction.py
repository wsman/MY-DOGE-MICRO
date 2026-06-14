"""Contract tests for MCP server client-facing error redaction (S006-002).

The MCP server runs locally, but the stdio/SSE transports can be consumed by
other processes. We must not leak absolute file paths or credential fragments
in tool error responses.
"""
import asyncio

import pytest

from doge.interfaces.mcp import server as srv


class TestMcpErrorRedaction:
    """Verify _sanitize_error and the _timed decorator redact sensitive data."""

    def test_sanitize_error_redacts_windows_path(self):
        exc = FileNotFoundError(
            "[Errno 2] No such file or directory: "
            "'D:\\Users\\WSMAN\\Desktop\\Coding Task\\MY-DOGE-MICRO\\data\\market.duckdb'"
        )
        sanitized = srv._sanitize_error(exc)
        assert "D:\\Users" not in sanitized
        assert "<path>" in sanitized
        assert sanitized.startswith("Error: FileNotFoundError:")

    def test_sanitize_error_redacts_unix_path(self):
        exc = PermissionError("cannot open /home/wsman/.doge/secrets.key")
        sanitized = srv._sanitize_error(exc)
        assert "/home/wsman" not in sanitized
        assert "<path>" in sanitized

    def test_sanitize_error_redacts_api_key(self):
        exc = RuntimeError(
            "network request failed: api_key=sk-abc123secretDEEPSEEKKeyXYZ "
            "and token='another-secret'"
        )
        sanitized = srv._sanitize_error(exc)
        assert "sk-abc123secretDEEPSEEKKeyXYZ" not in sanitized
        assert "another-secret" not in sanitized
        assert "api_key=<redacted>" in sanitized
        assert "token=<redacted>" in sanitized

    @pytest.mark.asyncio
    async def test_timed_decorator_returns_sanitized_error(self, monkeypatch):
        """A tool that raises with a path/key must return redacted text."""
        raw_path = "C:\\Users\\wsman\\data\\market.duckdb"
        raw_key = "sk-secret-leaked-key"

        @srv._timed("redacted_tool")
        async def failing_tool():
            raise RuntimeError(f"boom: {raw_path} key={raw_key}")

        result = await failing_tool()
        assert raw_path not in result
        assert raw_key not in result
        assert "<path>" in result
        assert "key=<redacted>" in result

    @pytest.mark.asyncio
    async def test_timed_decorator_timeout_string_stays_safe(self):
        """Timeout errors use the fixed safe string and do not include exc info."""

        @srv._timed("slow_tool")
        async def slow_tool():
            await asyncio.sleep(10)

        # Patch timeout to avoid waiting.
        original_timeout = srv.TOOL_TIMEOUT
        srv.TOOL_TIMEOUT = 0.001
        try:
            result = await slow_tool()
            assert "timed out after" in result
            assert "Error: asyncio.TimeoutError" not in result
        finally:
            srv.TOOL_TIMEOUT = original_timeout
