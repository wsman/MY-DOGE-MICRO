import yfinance as yf
import pandas as pd
import numpy as np
import logging
from typing import Optional
from .config import MacroConfig

logger = logging.getLogger(__name__)

class GlobalMacroLoader:
    def __init__(self, config: MacroConfig):
        self.config = config
        logger.info(f"初始化数据加载器，配置: {config}")

    def fetch_combined_data(self) -> Optional[pd.DataFrame]:
        """
        获取并清洗全球核心资产的历史价格数据。

        1. 下载包括科技股(QQQ)、黄金(GLD)、数字货币(BTC-USD)及A股(000300.SS)在内的多资产历史数据。
        2. 强制对齐到股票交易日（以 config.tech_proxy 为基准），剔除周末和节假日的非交易日期。
        3. 对缺失值进行前向填充，确保数据完整性。
        4. 截取指定数量的最近交易日数据作为最终输出。

        Returns:
            Optional[pd.DataFrame]: 包含所有资产价格的历史数据，按交易日对齐并截取最新 lookback_days 行。
            如果下载失败则返回 None。
        """
        tickers = [
            self.config.tech_proxy,
            self.config.safe_haven_proxy,
            self.config.target_asset
        ]

        # 动态添加 Crypto
        if hasattr(self.config, 'crypto_proxy') and self.config.crypto_proxy:
            tickers.append(self.config.crypto_proxy)

        logger.info(f"📡 正在从全球市场同步数据: {tickers} ...")

        # 配置代理
        proxy = None
        if self.config.proxy_enabled and self.config.proxy_url:
            proxy = self.config.proxy_url
            logger.info(f"🔗 使用代理: {proxy}")

        try:
            # 获取足够长的数据以确保 lookback window 有效（超额获取）
            fetch_days = int(self.config.lookback_days * 1.65) + 20
            data = yf.download(
                tickers=tickers,
                period=f"{fetch_days}d",
                interval="1d",
                auto_adjust=True,
                progress=False,
                proxy=proxy
            )

            if data is None or data.empty:
                logger.error("下载的数据为空")
                return None

            # 兼容性处理
            if isinstance(data.columns, pd.MultiIndex):
                try:
                    if 'Close' in data.columns.levels[0]:
                        data = data['Close']
                except:
                    pass

            # 数据清洗：对齐到股票交易日（以科技股代理资产为基准）
            data = data.dropna(subset=[self.config.tech_proxy])
            # 填充其他资产可能缺失的数据（如加密货币在交易日可能缺失）
            data = data.ffill()
            # 丢弃仍包含 NaN 的行（例如首行数据缺失）
            data = data.dropna()

            # 确保返回恰好指定数量的交易日数据（截取最后 N 行）
            if len(data) >= self.config.lookback_days:
                data = data.tail(self.config.lookback_days)
                logger.info(f"✅ 成功获取 {len(data)} 个交易日的数据")
            else:
                logger.warning(f"⚠️ 数据不足，仅获取到 {len(data)} 个交易日（配置要求: {self.config.lookback_days}）")
            
            return data

        except Exception as e:
            logger.error(f"数据下载失败: {e}")
            return None

    def get_market_summary(self, data: pd.DataFrame) -> dict:
        if data is None or data.empty:
            return {}
        latest = data.iloc[-1]

        summary = {
            'latest_date': str(data.index[-1].date()),
            'data_points': str(len(data)),
            'tech_price': f"{latest.get(self.config.tech_proxy, 0):.2f}",
            'gold_price': f"{latest.get(self.config.safe_haven_proxy, 0):.2f}",
            'target_price': f"{latest.get(self.config.target_asset, 0):.2f}"
        }

        if hasattr(self.config, 'crypto_proxy') and self.config.crypto_proxy in latest:
             summary['crypto_price'] = f"{latest.get(self.config.crypto_proxy, 0):.2f}"

        return summary

    def calculate_metrics(self, data: pd.DataFrame) -> dict:
        """
        计算分层级的时间序列指标：
        1. 波动率 (Vol)
        2. 中期趋势 (Medium Trend): 基于整个下载周期 (约120-180天)
        3. 短期动量 (Short Momentum): 基于最近5个交易日
        """
        try:
            # 基础数据
            returns = data.pct_change()
            # 年化波动率 (使用 lookback 窗口)
            vol_window = min(len(data), 60)
            volatility = returns.tail(vol_window).std() * np.sqrt(252)

            # 1. 中期趋势 (Whole Window)
            # Formula: (P_now - P_start) / P_start
            trend_medium = (data.iloc[-1] - data.iloc[0]) / data.iloc[0]

            # 2. 短期动量 (Last 5 Days)
            # Formula: (P_now - P_t-5) / P_t-5
            if len(data) >= 6:
                momentum_short = (data.iloc[-1] - data.iloc[-6]) / data.iloc[-6]
            else:
                momentum_short = trend_medium # Fallback

            # 3. 风险信号判断 (基于中期趋势)
            risk_on = trend_medium.get(self.config.tech_proxy, 0) > trend_medium.get(self.config.safe_haven_proxy, 0)

            metrics = {
                'metadata_days': len(data),
                'tech_volatility': float(volatility.get(self.config.tech_proxy, 0)),
                'risk_on_signal': bool(risk_on)
            }

            # 遍历所有资产，分别记录长短期指标
            for col in data.columns:
                metrics[f'{col}_trend_medium'] = float(trend_medium.get(col, 0))
                metrics[f'{col}_return_5d'] = float(momentum_short.get(col, 0))

            logger.info(f"📊 指标计算完成 (Days={len(data)})")
            return metrics
        except Exception as e:
            logger.error(f"指标计算错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
