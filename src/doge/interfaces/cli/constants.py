"""Shared CLI constants: exit codes and bilingual strings."""

EXIT_NO_DATA = 1

# Bilingual strings preserved from legacy macro CLI.
MACRO_START_MSG = "🚀 启动 MY-DOGE 宏观战略分析 (Verbose Mode)..."
MACRO_CONFIG_OK_MSG = "✅ 配置加载成功"
MACRO_MARKET_SUMMARY_PREFIX = "📊 市场数据摘要:"
MACRO_NO_DATA_MSG = "❌ 无法获取市场数据，请检查网络连接"
MACRO_FAIL_PREFIX = "❌ 运行失败:"
MACRO_API_KEY_HINT_ZH = "💡 若与 API Key 有关，请检查 DEEPSEEK_API_KEY 环境变量配置"
MACRO_API_KEY_HINT_EN = "If this is API-key related, check the DEEPSEEK_API_KEY env var."

# Demo final line (legacy).
DEMO_MACRO_HINT = "For LLM-powered reports, set DEEPSEEK_API_KEY and run: doge macro"
