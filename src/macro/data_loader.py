import yfinance as yf
import pandas as pd
import numpy as np
import logging
import os
import requests
import time
from typing import Optional
from scipy import stats
from .config import MacroConfig

logger = logging.getLogger(__name__)

class GlobalMacroLoader:
    def __init__(self, config: MacroConfig):
        self.config = config
        logger.info(f"初始化数据加载器，配置: {config}")

    def fetch_combined_data(self, max_retries: int = 3, retry_delay: float = 5.0) -> Optional[pd.DataFrame]:
        """
        获取并清洗全球核心资产的历史价格数据。

        1. 下载包括科技股(QQQ)、黄金(GLD)、数字货币(BTC-USD)及A股(000300.SS)在内的多资产历史数据。
        2. 强制对齐到股票交易日（以 config.tech_proxy 为基准），剔除周末和节假日的非交易日期。
        3. 对缺失值进行前向填充，确保数据完整性。
        4. 截取指定数量的最近交易日数据作为最终输出。

        Args:
            max_retries: 最大重试次数（默认3次）
            retry_delay: 重试间隔秒数（默认5秒）

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

        logger.info(f"正在从全球市场同步数据: {tickers} ...")

        # 配置代理：通过环境变量设置，让 yfinance 内部处理
        # 注意：新版本 yfinance 要求使用 curl_cffi 会话，不支持直接传入 requests.Session
        # 因此改为设置环境变量，让 yfinance 自动使用代理
        original_http_proxy = None
        original_https_proxy = None
        if self.config.proxy_enabled and self.config.proxy_url:
            proxy_url = self.config.proxy_url
            # 保存原始环境变量值
            original_http_proxy = os.environ.get('HTTP_PROXY')
            original_https_proxy = os.environ.get('HTTPS_PROXY')
            # 设置代理环境变量
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
            logger.info(f"🔗 使用代理: {proxy_url}")

        try:
            # 获取足够长的数据以确保 lookback window 有效（超额获取）
            fetch_days = int(self.config.lookback_days * 1.65) + 20
            
            # 重试机制：解决 Yahoo Finance API 速率限制问题
            last_error = None
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"第 {attempt + 1} 次重试（共 {max_retries} 次）...")
                        time.sleep(retry_delay)
                    
                    data = yf.download(
                        tickers=tickers,
                        period=f"{fetch_days}d",
                        interval="1d",
                        auto_adjust=True,
                        progress=False
                    )
                    
                    # 检查是否返回空数据
                    if data is None or data.empty:
                        logger.warning(f"下载返回空数据，可能是速率限制")
                        continue
                    
                    # 成功获取数据，跳出重试循环
                    break
                    
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    if "Rate" in error_msg or "429" in error_msg or "Too Many Requests" in error_msg:
                        logger.warning(f"触发 Yahoo Finance 速率限制，等待 {retry_delay} 秒后重试...")
                    else:
                        logger.error(f"下载出错: {e}")
            else:
                # 所有重试都失败
                logger.error(f"数据下载失败，已重试 {max_retries} 次")
                return None

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
            tech_col = str(self.config.tech_proxy)
            data = data.dropna(subset=[tech_col])  # type: ignore
            # 填充其他资产可能缺失的数据（如加密货币在交易日可能缺失）
            data = data.ffill()
            # 丢弃仍包含 NaN 的行（例如首行数据缺失）
            data = data.dropna()

            # 确保返回恰好指定数量的交易日数据（截取最后 N 行）
            if len(data) >= self.config.lookback_days:
                data = data.tail(self.config.lookback_days)
                logger.info(f"成功获取 {len(data)} 个交易日的数据")
            else:
                logger.warning(f"数据不足，仅获取到 {len(data)} 个交易日（配置要求: {self.config.lookback_days}）")
            
            return data
            
        except Exception as e:
            logger.error(f"数据下载失败: {e}")
            return None
            
        finally:
            # 恢复原始环境变量
            if self.config.proxy_enabled and self.config.proxy_url:
                if original_http_proxy is not None:
                    os.environ['HTTP_PROXY'] = original_http_proxy
                else:
                    os.environ.pop('HTTP_PROXY', None)
                    
                if original_https_proxy is not None:
                    os.environ['HTTPS_PROXY'] = original_https_proxy
                else:
                    os.environ.pop('HTTPS_PROXY', None)

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

    def calculate_rsrs(self, prices: pd.Series, window: int = 18) -> float:
        """
        计算 RSRS (阻力支撑相对强度)
        简化版：基于收盘价的线性回归斜率，返回趋势强度值。
        
        参数:
            prices: 价格序列
            window: 回归窗口（默认18）
        
        返回:
            float: 趋势强度值，范围在 -1.0 到 1.0 之间。
            - 正值表示上涨趋势，负值表示下跌趋势
            - 绝对值越大表示趋势越强（R² 越大，趋势越纯粹）
            - 例如：RSRS > 0.8 代表极强上涨趋势，RSRS < -0.8 代表极强下跌趋势
        """
        if len(prices) < window:
            return 0.0
        
        y = prices.iloc[-window:].values
        x = np.arange(len(y))
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # 将 R2 * Slope 符号作为趋势强度
        # R² (0~1) 代表趋势的纯度，乘以 slope 的符号 (+1/-1)
        trend_strength = (r_value ** 2) * (1 if slope > 0 else -1)
        return trend_strength

    def calculate_volatility_skew(self, prices: pd.Series, short_win=5, long_win=20) -> float:
        """
        计算波动率偏度: 短期波动率 / 长期波动率
        """
        ret = prices.pct_change()
        vol_short = ret.rolling(window=short_win).std().iloc[-1]
        vol_long = ret.rolling(window=long_win).std().iloc[-1]
        
        if vol_long == 0 or np.isnan(vol_long):
            return 1.0
            
        return vol_short / vol_long

    def calculate_advanced_metrics(self, prices_df: pd.DataFrame, window: Optional[int] = None) -> pd.DataFrame:
        """
        计算高级宏观指标：Z-Score 偏离度与波动率缩放因子

        参数:
            prices_df: 包含资产价格的历史数据，列名应与 config 中定义的资产符号一致。
            window: 滚动窗口大小，默认为 config.volatility_window

        返回:
            添加了高级指标列的 DataFrame，已剔除 NaN。
        """
        win = window if window is not None else self.config.volatility_window

        # 确保没有 undefined symbols: 检查输入数据完整性
        required_cols = [
            self.config.safe_haven_proxy,
            self.config.crypto_proxy,
            self.config.tech_proxy
        ]
        if not all(col in prices_df.columns for col in required_cols):
            raise ValueError(f"缺少必要资产数据: {required_cols}")

        # 创建副本以避免修改原数据
        df = prices_df.copy()

        # 1. 计算金/币比值 (Gold/BTC Ratio)
        # 避免分母为零
        denominator = df[self.config.crypto_proxy].replace(0, np.nan)
        df['gold_btc_ratio'] = df[self.config.safe_haven_proxy] / denominator

        # 2. 计算 Z-Score (Rolling)
        mean = df['gold_btc_ratio'].rolling(window=win).mean()
        std = df['gold_btc_ratio'].rolling(window=win).std()
        df['ratio_z_score'] = (df['gold_btc_ratio'] - mean) / std

        # 3. 计算实现波动率 (Realized Volatility)
        # 使用对数收益率
        df['log_ret'] = np.log(df[self.config.tech_proxy] / df[self.config.tech_proxy].shift(1))
        ann_vol = df['log_ret'].rolling(window=win).std() * np.sqrt(252)

        # 4. 风险控制：波动率倒数加权 (Risk Parity Logic)
        df['vol_scale_factor'] = 1.0 / ann_vol.replace(0, np.nan)
        
        # 5. [NEW] 波动率偏度 (Vol Skew) - 针对科技股
        # 计算滚动波动率偏度
        tech_ret = df[self.config.tech_proxy].pct_change()
        df['vol_short'] = tech_ret.rolling(window=5).std()
        df['vol_long'] = tech_ret.rolling(window=20).std()
        df['vol_skew'] = df['vol_short'] / df['vol_long']

        # 6. [NEW] Amihud Illiquidity (简化版)
        # 由于缺乏 Volume 数据，我们使用 |Return| / Price 作为波动效率的替代指标
        # 或者暂时略过，因为 fetch_combined_data 丢弃了 Volume
        # 这里我们用 "价格效率" 代替：|Ret| / Volatility
        # 值越小，代表单位波动带来的涨跌幅越小（效率低）
        df['price_efficiency'] = df['log_ret'].abs() / (ann_vol / np.sqrt(252))

        return df.dropna()

    def calculate_metrics(self, data: pd.DataFrame) -> dict:
        """
        计算分层级的时间序列指标：
        1. 波动率 (Vol)
        2. 中期趋势 (Medium Trend): 基于整个下载周期 (约120-180天)
        3. 短期动量 (Short Momentum): 基于最近5个交易日
        4. 高级指标: 金/币比值、Z-Score、波动率缩放因子
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

            # 4. 高级指标计算
            advanced_df = self.calculate_advanced_metrics(data)
            latest_advanced = advanced_df.iloc[-1] if not advanced_df.empty else {}

            metrics = {
                'metadata_days': len(data),
                'tech_volatility': float(volatility.get(self.config.tech_proxy, 0)),
                'risk_on_signal': bool(risk_on)
            }

            # 遍历所有资产，分别记录长短期指标
            for col in data.columns:
                metrics[f'{col}_trend_medium'] = float(trend_medium.get(col, 0))
                metrics[f'{col}_return_5d'] = float(momentum_short.get(col, 0))

            # 添加高级指标
            if not advanced_df.empty:
                metrics['gold_btc_ratio'] = float(latest_advanced.get('gold_btc_ratio', 0))
                metrics['ratio_z_score'] = float(latest_advanced.get('ratio_z_score', 0))
                metrics['vol_scale_factor'] = float(latest_advanced.get('vol_scale_factor', 0))
                metrics['vol_skew'] = float(latest_advanced.get('vol_skew', 0))
                
                # 计算 RSRS (简化版 - 基于 Close 斜率)
                # 对主要资产计算
                for col in [self.config.tech_proxy, self.config.safe_haven_proxy]:
                    rsrs_val = self.calculate_rsrs(data[col])
                    metrics[f'{col}_rsrs'] = float(rsrs_val)

            logger.info(f"📊 指标计算完成 (Days={len(data)})")
            return metrics
        except Exception as e:
            logger.error(f"指标计算错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}