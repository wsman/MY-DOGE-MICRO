import builtins

from doge.infrastructure.data_source.tdx_server_list import ConfigTDXServerList


def test_tdx_server_list_reads_configured_servers():
    adapter = ConfigTDXServerList()

    cn = adapter.list_servers("cn")
    us = adapter.list_servers("us")

    assert cn
    assert us
    assert cn[0].port == 7709
    assert us[0].port == 7727


def test_tdx_server_test_degrades_when_opentdx_unavailable(monkeypatch):
    original_import = builtins.__import__

    def _blocking_import(name, *args, **kwargs):
        if name == "opentdx" or name.startswith("opentdx."):
            raise ImportError("blocked")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocking_import)

    result = ConfigTDXServerList().test_server("127.0.0.1", "cn")

    assert result.ok is False
    assert result.error == "opentdx unavailable"
