#!/usr/bin/env python3
"""
MY-DOGE 宏观战略分析包的命令行接口
"""

import argparse
import sys
import os
import logging  # 添加导入
import re
from typing import Optional

# Force UTF-8 stdout on Windows (and any platform with a narrow console encoding)
# so emoji/Chinese output never raises UnicodeEncodeError. This process-wide guard
# catches any remaining print() calls in legacy macro modules that do not use
# _safe_print.
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name)
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# S002-009 / TR-011: the macro package is importable via the editable install,
# so ``from . import ...`` resolves without a sys.path shim (ADR-0001 forbidden
# pattern ``sys_path_insert``). NOTE: running ``python src/macro/cli.py``
# directly still fails on the relative import (it must be launched as
# ``python -m macro.cli``); that limitation is pre-existing and unchanged.
from . import MacroConfig, GlobalMacroLoader, DeepSeekStrategist, setup_logging


def _redact_secrets(text: str, config: Optional[MacroConfig] = None) -> str:
    """Remove the real api_key and the placeholder sentinel from text.

    As defense-in-depth, any sk-... token that looks like an OpenAI-style
    API key is also masked, so exceptions raised before ``config`` is bound
    cannot leak a key either.
    """
    secrets = ["REPLACE_WITH_DEEPSEEK_API_KEY"]
    if config is not None and config.api_key:
        secrets.append(config.api_key)
    safe = text
    for secret in secrets:
        if secret:
            safe = safe.replace(secret, "<redacted>")
    # Belt-and-braces: mask any sk-... API-key-like token that may have
    # escaped into the message before config was loaded.
    safe = re.sub(r"sk-[A-Za-z0-9_-]{20,}", "<redacted>", safe)
    return safe


def _safe_print(text: str) -> None:
    """Print *text* to stdout, falling back to ascii/emoji-stripped on encoding errors."""
    try:
        sys.stdout.buffer.write(text.encode("utf-8", "replace") + b"\n")
        return
    except Exception:
        pass
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            encoded = text.encode(sys.stdout.encoding or "utf-8", "replace")
            sys.stdout.buffer.write(encoded + b"\n")
        except Exception:  # pragma: no cover - last-resort fallback
            print(text.encode("ascii", "ignore").decode("ascii"))


def main():
    """主函数 - 命令行接口"""

    parser = argparse.ArgumentParser(
        description="MY-DOGE 宏观战略分析包 - 量化宏观对冲策略工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  my-doge-macro                    # 运行基本分析
  my-doge-macro --verbose          # 详细输出模式
  my-doge-macro --config-file config.json  # 指定配置文件
        """
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细输出"
    )

    parser.add_argument(
        "--config-file",
        help="指定配置文件路径（暂未实现）"
    )

    args = parser.parse_args()

    _safe_print("🚀 启动 MY-DOGE 宏观战略分析 (Verbose Mode)...")

    try:
        # --- 修改部分开始 ---
        # 强制默认开启详细模式 (DEBUG)
        # 如果未来需要静默模式，可以添加 --quiet 参数
        log_level = logging.DEBUG

        # 初始化日志系统
        setup_logging(log_level=log_level)
        # --- 修改部分结束 ---

        # 创建配置
        config = MacroConfig()
        _safe_print(f"✅ 配置加载成功")

        # 获取市场数据
        loader = GlobalMacroLoader(config)
        market_data = loader.fetch_combined_data()

        if market_data is not None:
            # 显示市场摘要
            summary = loader.get_market_summary(market_data)
            _safe_print(f"📊 市场数据摘要: {summary}")

            # 计算技术指标
            metrics = loader.calculate_metrics(market_data)

            # DeepSeek 分析
            strategist = DeepSeekStrategist(config)
            raw_report = strategist.generate_strategy_report(metrics, market_data)

            # 格式化报告
            formatted_report = strategist.format_report_for_display(raw_report, metrics)
            _safe_print(formatted_report)

        else:
            _safe_print("❌ 无法获取市场数据，请检查网络连接")
            sys.exit(1)

    except Exception as e:
        safe_msg = _redact_secrets(str(e), locals().get("config"))
        _safe_print(f"❌ 运行失败: {safe_msg}")
        _safe_print("💡 若与 API Key 有关，请检查 DEEPSEEK_API_KEY 环境变量配置")
        _safe_print("   If this is API-key related, check the DEEPSEEK_API_KEY env var.")
        sys.exit(1)


if __name__ == "__main__":
    main()
