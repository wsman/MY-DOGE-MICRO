"""Tests for the new ILLMClient port and DeepSeekClient adapter."""

from abc import ABC

from doge.core.ports.llm import ILLMClient
from doge.infrastructure.llm.deepseek_client import DeepSeekClient


class TestILLMClientPort:
    def test_illm_client_is_abstract(self):
        assert issubclass(ILLMClient, ABC)

    def test_illm_client_chat_signature(self):
        """The port declares the expected chat signature."""
        assert hasattr(ILLMClient, "chat")

    def test_deepseek_client_is_illm_client(self):
        assert issubclass(DeepSeekClient, ILLMClient)

    def test_deepseek_client_returns_none_without_api_key(self, monkeypatch):
        """Without DEEPSEEK_API_KEY the adapter degrades to None."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        from doge.config.settings import reset_settings
        reset_settings()

        client = DeepSeekClient()
        result = client.chat("system", "user")
        assert result is None

    def test_deepseek_client_returns_none_with_empty_api_key(self, monkeypatch):
        """An empty DEEPSEEK_API_KEY is treated as missing."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "")
        from doge.config.settings import reset_settings
        reset_settings()

        client = DeepSeekClient()
        result = client.chat("system", "user")
        assert result is None
