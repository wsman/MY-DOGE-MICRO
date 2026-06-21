"""TDX server-list adapter."""

from __future__ import annotations

import time

from doge.config import get_settings
from doge.core.ports.tdx_server_list import ITDXServerList, TDXServer


class ConfigTDXServerList(ITDXServerList):
    """Expose configured TDX servers without importing legacy downloader code."""

    def list_servers(self, market: str) -> list[TDXServer]:
        settings = get_settings().tdx
        if market == "cn":
            return [TDXServer(host=host, port=settings.cn_port) for host in settings.cn_servers]
        return [TDXServer(host=host, port=settings.us_port) for host in settings.us_servers]

    def test_server(self, host: str, market: str) -> TDXServer:
        settings = get_settings().tdx
        port = settings.cn_port if market == "cn" else settings.us_port
        try:
            from opentdx.tdxClient import TdxClient  # type: ignore[import-not-found]
        except ImportError:
            return TDXServer(host=host, port=port, ok=False, error="opentdx unavailable")

        client = TdxClient()
        started = time.time()
        try:
            client.quotation_client.connect(host, port=port, time_out=settings.timeout)
            client.quotation_client.login()
            if market == "us":
                client.ex_quotation_client.connect(host, port=settings.us_port, time_out=settings.timeout)
                client.ex_quotation_client.login()
            latency_ms = int((time.time() - started) * 1000)
            return TDXServer(host=host, port=port, ok=True, latency_ms=latency_ms)
        except Exception as exc:  # noqa: BLE001 - server probes fail in provider-specific ways
            return TDXServer(host=host, port=port, ok=False, error=str(exc))
        finally:
            try:
                client.quotation_client.disconnect()
                if market == "us":
                    client.ex_quotation_client.disconnect()
            except Exception:
                pass
