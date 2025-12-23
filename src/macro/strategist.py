import logging
from openai import OpenAI
import pandas as pd
from .config import MacroConfig
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class DeepSeekStrategist:
    def __init__(self, config: MacroConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )
        logger.info("初始化 DeepSeek 策略分析师 (Precision Mode)")

    def generate_strategy_report(self, metrics: dict, market_data: pd.DataFrame) -> str:
        logger.info("🧠 DeepSeek 正在进行宏观推理...")

        crypto = getattr(self.config, 'crypto_proxy', 'BTC-USD')
        days_count = metrics.get('metadata_days', 'N/A')

        # --- 构造结构化数据块 (Structured Context) ---
        # 这种格式让 LLM 更容易引用具体数字
        context_str = f"分析周期说明: 中期趋势基于过去 {days_count} 个交易日，短期动量基于过去 5 个交易日。\n\n"

        # 修改后 (完全动态化):
        assets = [
            (self.config.tech_name, self.config.tech_proxy),
            (self.config.safe_name, self.config.safe_haven_proxy),
            (self.config.crypto_name, crypto),
            (self.config.target_name, self.config.target_asset)
        ]

        for name, ticker in assets:
            if ticker:
                med = metrics.get(f'{ticker}_trend_medium', 0)
                short = metrics.get(f'{ticker}_return_5d', 0)
                context_str += f"Asset: {name} ({ticker})\n"
                context_str += f"  - [数据: {days_count}个交易日趋势]: {med:+.2%}\n"
                context_str += f"  - [数据: 近5日涨跌]: {short:+.2%}\n"

        context_str += f"\nMarket Volatility (Annualized): {metrics.get('tech_volatility', 0):.2%}\n"
        context_str += f"Risk Signal: {'Risk-On' if metrics.get('risk_on_signal') else 'Risk-Off'}\n"

        # [NEW] Quantitative Dashboard Data
        tech_rsrs = metrics.get(f'{self.config.tech_proxy}_rsrs', 0)
        vol_skew = metrics.get('vol_skew', 0)
        
        dashboard_data = f"""
### 3. 量化风控仪表盘 (Quantitative Dashboard)

| 维度 | 指标名称 | 当前读数 | 信号解读 |
| :--- | :--- | :--- | :--- |
| **趋势** | **RSRS (Slope*R2)** | **{tech_rsrs:.2f}** | (正值代表多头趋势，负值代表空头，绝对值越大趋势越强) |
| **情绪** | **Vol Skew (5/20)**| **{vol_skew:.2f}** | (>1.5 恐慌加速; <0.8 极度平静/变盘前夕) |
| **资金** | **Risk Signal** | {'Risk-On' if metrics.get('risk_on_signal') else 'Risk-Off'} | (基于中期趋势比较) |
"""

        # --- Prompt Engineering ---
        system_prompt = f"""你是一位讲究数据证据的量化宏观分析师。
你的任务是根据提供的长短期指标分析市场状态，并生成一份包含【量化风控仪表盘】的专业报告。

【核心规则 - 必须严格遵守】
1. 你的每一条分析结论，必须明确引用数据来源。
2. 引用格式必须包含方括号，例如：
   - "科技股长期走强 [数据: 120天趋势 +5.2%]"
   - "但短期出现回调 [数据: 近5日涨跌 -1.3%]"
3. 严禁混淆短期波动和长期趋势。
4. 必须对比 BTC 与 QQQ（风险属性）以及 BTC 与 GLD（避险属性）的相关性数据。
5. **必须在报告中包含【量化风控仪表盘】章节**，直接使用我提供的数据填充表格，并对 RSRS 和 Vol Skew 进行专业解读。
   - RSRS > 0 且数值较大 -> 趋势强劲
   - Vol Skew < 0.8 -> 变盘节点
   - Vol Skew > 1.5 -> 风险释放中
"""

        # 获取近期数据用于展示（例如在提示词中）
        recent_data_for_prompt = market_data.tail(5)
        
        user_prompt = f"""
        【结构化市场数据】
        {context_str}

        【量化仪表盘数据】
        {dashboard_data}

        【最近5日价格明细】
        {recent_data_for_prompt.to_string()}

        请生成一份简明扼要的策略报告 (v2.0)，分析上述资产的宏观状态并给出操作建议。
        请务必在报告中包含 "3. 量化风控仪表盘 (Quantitative Dashboard)" 章节。
        """

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                stream=False,
                temperature=0.6 # 降低随机性，提高精确度
            )

            content = response.choices[0].message.content
            logger.info("✅ DeepSeek 分析完成")

            if not content:
                return "分析完成，但API返回内容为空。"
            
            # 计算数据范围和资产列表
            trading_days = len(market_data)
            calendar_days = (market_data.index.max() - market_data.index.min()).days
            start_date = market_data.index.min().strftime('%Y-%m-%d')
            end_date = market_data.index.max().strftime('%Y-%m-%d')
            assets = ", ".join([col for col in market_data.columns if col != 'Date'])
            
            # 生成完整报告 (带标题)
            full_report = self.format_report_for_display(content, metrics, start_date, end_date, assets, trading_days, calendar_days)
            
            # 自动归档报告到文件
            try:
                report_dir = "macro_report"
                os.makedirs(report_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"{report_dir}/{timestamp}_macro.md"
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(full_report)
                print(f"✅ 宏观报告已归档至: {filename}")
            except Exception as e:
                print(f"❌ 报告归档失败: {str(e)}")
            
            return content

        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            return None

    def format_report_for_display(self, raw_report: str, metrics: dict, start_date=None, end_date=None, assets=None, trading_days=None, calendar_days=None) -> str:
        if not raw_report:
            return "⚠️ 报告为空"

        risk_signal = '🟢 RISK-ON' if metrics.get('risk_on_signal') else '🔴 RISK-OFF'
        volatility = metrics.get('tech_volatility', 0)

        # 构建数据描述块
        if start_date and end_date and assets:
            if trading_days is not None and calendar_days is not None:
                header_info = f"""
> 🕒 **数据溯源**：{start_date} 至 {end_date} （历时 {calendar_days} 个自然日，覆盖 **{trading_days}** 个交易日）
> 🌍 **资产覆盖**：{assets}
---
"""
            else:
                header_info = f"""
> 🕒 **数据溯源**：本次报告基于 **{start_date}** 至 **{end_date}** 的历史数据。
> 🌍 **资产覆盖**：{assets}
---
"""
        else:
            header_info = ""

        header = f"""# MY-DOGE PRECISION MACRO REPORT

{header_info}Risk Signal: {risk_signal}
Volatility : {volatility:.2%}
---"""
        return header + raw_report
