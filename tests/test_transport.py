"""Transport-level tests for the MCP server."""
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
SERVER_SCRIPT = PROJECT_ROOT / "mcp_server.py"


class TestStdioTransport:
    """Verify stdio JSON-RPC initialization handshake."""

    def test_stdio_initialize(self):
        proc = subprocess.Popen(
            [PYTHON, str(SERVER_SCRIPT), "--transport", "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        try:
            init_req = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                },
            })
            proc.stdin.write(init_req + "\n")
            proc.stdin.flush()

            # Read response line-by-line until we get JSON
            raw = ""
            for _ in range(30):
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    raw = line
                    break
                time.sleep(0.1)

            assert raw, "No response from stdio server"
            resp = json.loads(raw)
            assert resp.get("jsonrpc") == "2.0"
            assert resp.get("id") == 1
            result = resp.get("result", {})
            assert "serverInfo" in result
            assert result["serverInfo"]["name"] == "doge-db"
        finally:
            proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)


class TestSseTransport:
    """Verify SSE HTTP endpoints."""

    @pytest.fixture(scope="class")
    def sse_url(self):
        import socket
        import threading
        import uvicorn
        import sys

        # Find a free port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()

        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        from mcp_server import mcp

        app = mcp.sse_app()
        server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning"))
        t = threading.Thread(target=server.run, daemon=True)
        t.start()

        # Wait for startup
        for _ in range(50):
            try:
                import urllib.request
                with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=0.5) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(0.1)
        else:
            pytest.fail("SSE server did not start in time")

        yield f"http://{host}:{port}"

        server.should_exit = True
        t.join(timeout=5)

    def test_health_endpoint(self, sse_url):
        import urllib.request
        req = urllib.request.Request(f"{sse_url}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            body = json.loads(resp.read().decode())
            assert body["status"] == "ok"

    def test_metrics_endpoint(self, sse_url):
        import urllib.request
        req = urllib.request.Request(f"{sse_url}/metrics")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            text = resp.read().decode()
            assert "mcp_requests_total" in text or "# no metrics yet" in text

    def test_sse_endpoint_exists(self, sse_url):
        import urllib.request
        req = urllib.request.Request(f"{sse_url}/sse")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
