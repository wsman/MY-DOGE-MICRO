"""Tests preserving bilingual output strings from the legacy macro CLI."""

import macro.cli as macro_cli
from doge.interfaces.cli import constants


class TestBilingualOutput:
    def test_start_message_preserved(self):
        assert "启动 MY-DOGE 宏观战略分析" in constants.MACRO_START_MSG

    def test_config_ok_message_preserved(self):
        assert "配置加载成功" in constants.MACRO_CONFIG_OK_MSG

    def test_market_summary_prefix_preserved(self):
        assert "市场数据摘要" in constants.MACRO_MARKET_SUMMARY_PREFIX

    def test_no_data_message_preserved(self):
        assert "无法获取市场数据" in constants.MACRO_NO_DATA_MSG

    def test_fail_prefix_preserved(self):
        assert "运行失败" in constants.MACRO_FAIL_PREFIX

    def test_api_key_hint_chinese_preserved(self):
        assert "DEEPSEEK_API_KEY 环境变量配置" in constants.MACRO_API_KEY_HINT_ZH

    def test_api_key_hint_english_preserved(self):
        assert "DEEPSEEK_API_KEY env var" in constants.MACRO_API_KEY_HINT_EN

    def test_redact_function_masks_placeholder(self):
        text = macro_cli._redact_secrets("error: REPLACE_WITH_DEEPSEEK_API_KEY leaked")
        assert "REPLACE_WITH_DEEPSEEK_API_KEY" not in text
        assert "<redacted>" in text

    def test_redact_function_masks_sk_token(self):
        fake_key = "sk-fake-test-key-not-real-1234567890"
        text = macro_cli._redact_secrets(f"error: {fake_key}")
        assert fake_key not in text
        assert "<redacted>" in text
