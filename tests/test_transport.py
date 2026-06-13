"""Transport-level tests for the MCP server."""
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
SERVER_SCRIPT = PROJECT_ROOT / "doge_mcp.py"


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

        # Editable install resolves ``doge`` as a top-level package; no
        # sys.path shim needed. Build the modular server via its factory.
        from doge.interfaces.mcp.server import create_mcp_server

        mcp = create_mcp_server()
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
        """The SSE endpoint accepts connections and emits the initial event.

        SSE is an infinite stream, so a bare ``urllib.request.urlopen`` would
        block forever waiting for the response body to finish. We open a raw
        socket, assert the response headers, read until the first ``endpoint``
        event arrives (or a short read timeout elapses), and then close.
        """
        import socket
        import urllib.parse

        parsed = urllib.parse.urlparse(sse_url)
        sock = socket.create_connection((parsed.hostname, parsed.port), timeout=5)
        try:
            request = f"GET /sse HTTP/1.1\r\nHost: {parsed.hostname}:{parsed.port}\r\n\r\n"
            sock.sendall(request.encode("ascii"))
            # The endpoint event should arrive immediately; give it a short
            # window and stop as soon as we see it.
            sock.settimeout(1.0)
            data = b""
            try:
                while True:
                    chunk = sock.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                    if b"event: endpoint" in data:
                        break
            except socket.timeout:
                pass

            assert b"HTTP/1.1 200 OK" in data, f"expected 200, got: {data[:200]!r}"
            assert b"text/event-stream" in data, f"expected SSE content type, got: {data[:200]!r}"
            assert b"event: endpoint" in data, "initial endpoint event not received"
        finally:
            sock.close()
