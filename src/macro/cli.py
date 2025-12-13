#!/usr/bin/env python3
"""
MY-DOGE 宏观战略分析包的命令行接口
"""

import argparse
import sys
import os
import logging  # 添加导入

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from . import MacroConfig, GlobalMacroLoader, DeepSeekStrategist, setup_logging


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

    # --- 修改部分开始 ---
    # 强制默认开启详细模式 (DEBUG)
    # 如果未来需要静默模式，可以添加 --quiet 参数
    log_level = logging.DEBUG
    
    # 初始化日志系统
    setup_logging(log_level=log_level)
    # --- 修改部分结束 ---

    print("🚀 启动 MY-DOGE 宏观战略分析 (Verbose Mode)...")

    try:
        # 创建配置
        config = MacroConfig()
        print(f"✅ 配置加载成功")

        # 获取市场数据
        loader = GlobalMacroLoader(config)
        market_data = loader.fetch_combined_data()

        if market_data is not None:
            # 显示市场摘要
            summary = loader.get_market_summary(market_data)
            print(f"📊 市场数据摘要: {summary}")

            # 计算技术指标
            metrics = loader.calculate_metrics(market_data)

            # DeepSeek 分析
            strategist = DeepSeekStrategist(config)
            raw_report = strategist.generate_strategy_report(metrics, market_data)

            # 格式化报告
            formatted_report = strategist.format_report_for_display(raw_report, metrics)
            print(formatted_report)

        else:
            print("❌ 无法获取市场数据，请检查网络连接")
            sys.exit(1)

    except Exception as e:
        print(f"❌ 运行失败: {e}")
        print("💡 请检查 .env 文件中的 API Key 配置")
        sys.exit(1)


if __name__ == "__main__":
    main()
