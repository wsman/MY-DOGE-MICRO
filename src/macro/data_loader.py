import yfinance as yf  # noqa: F401 — retained for compatibility shims / tests
import pandas as pd
import numpy as np
import logging
import os
import requests
from typing import Optional
from scipy import stats
from .config import MacroConfig

# S005-006 / ADR-0004 Migration Plan step 2: the legacy macro-layer retry loop
# delegates to the shared MarketDataSource helper. This import crosses from
# ``src/macro`` (legacy) into ``src/doge.infrastructure`` (clean tree) — the
# intended migration direction per ADR-0004.
#
# S005-007 / ADR-0004 Migration Plan step 4: ``fetch_combined_data`` is now
# routed through ``YFinanceDataSource`` (the IMarketDataSource adapter),
# closing the last direct ``yfinance.download`` call in the macro engine.
# The adapter returns a long 8-column frame; this module pivots/merges the
# per-ticker frames into the WIDE Close-only frame (DatetimeIndex + columns
# = ticker symbols) that ``calculate_metrics`` / ``calculate_advanced_metrics``
# / ``DeepSeekStrategist`` consume. Behavior at the strategist boundary is
# preserved — only the data SOURCE changes (direct yfinance → adapter).
from doge.infrastructure.data_source._retry import fetch_with_retry, is_rate_limited
from doge.infrastructure.data_source.yfinance import YFinanceDataSource

logger = logging.getLogger(__name__)

class GlobalMacroLoader:
    def __init__(self, config: MacroConfig):
        self.config = config
        logger.info(
            "初始化数据加载器，资产: %s/%s/%s/%s, 回看: %s天",
            config.tech_proxy,
            config.safe_haven_proxy,
            config.crypto_proxy,
            config.target_asset,
            config.lookback_days,
        )

    def fetch_combined_data(self, max_retries: int = 3, retry_delay: float = 5.0) -> Optional[pd.DataFrame]:
        """
        获取并清洗全球核心资产的历史价格数据。

        1. 通过 ``YFinanceDataSource``（ADR-0004 MarketDataSource 适配器）下载
           包括科技股(QQQ)、黄金(GLD)、数字货币(BTC-USD)及A股(000300.SS)在内
           的多资产历史数据。S005-007 / ADR-0004 Migration Plan step 4: 原直接
           ``yfinance.download`` 调用已路由到适配器；适配器返回 LONG 8-col 帧
           (``date, open, high, low, close, volume, amount, ticker``)，本方法
           将其 pivot/merge 为 strategist 期望的 WIDE Close-only 帧
           (DatetimeIndex + columns=tickers)。
        2. 强制对齐到股票交易日（以 config.tech_proxy 为基准），剔除周末和节假日的非交易日期。
        3. 对缺失值进行前向填充，确保数据完整性。
        4. 截取指定数量的最近交易日数据作为最终输出。

        Args:
            max_retries: 最大重试次数（默认3次）。适配器内部已自带重试逻辑；
                此参数作为整体多资产下载的外层重试边界，保留以便单元测试
                控制（``retry_delay=0``）。
            retry_delay: 重试间隔秒数（默认5秒）。

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
        # 因此改为设置环境变量，让 yfinance 自动使用代理。
        # S005-007: ``YFinanceDataSource`` 自身不触碰代理环境变量
        # (data-sources.md §7)，沿用调用方进程的代理设置，因此继续在
        # 宏观层做 set/restore —— 与原直接调用路径保持完全一致。
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
            # 获取足够长的数据以确保 lookback window 有效（超额获取）。
            # ``calculate_advanced_metrics`` 需要 20-day 滚动窗口 + NaN-drop，
            # 因此过度获取 lookback_days * 1.65 + 20 天。S005-007 trap-1 修复
            # 后，适配器 ``download_kline(count=fetch_days)`` 会实际获取
            # max(fetch_days, period_days) 天，不再受 120-day period 限制。
            fetch_days = int(self.config.lookback_days * 1.65) + 20

            # 重试机制：解决 Yahoo Finance API 速率限制问题。
            # S005-006 / ADR-0004: 委托给共享 ``_retry.fetch_with_retry`` 助手。
            # S005-007: 实际抓取通过 ``YFinanceDataSource.download_kline``
            # 完成（适配器内部同样委托给 ``_retry.fetch_with_retry``）；
            # 此处的外层重试包裹多资产下载的整体边界，保留 None-on-exhaustion
            # 与速率限制日志语义，与原 ``yf.download`` 路径行为一致。
            def _on_retry(attempt: int, max_retries: int, exc: BaseException) -> None:
                if is_rate_limited(exc):
                    logger.warning(f"触发 Yahoo Finance 速率限制，等待 {retry_delay} 秒后重试...")
                else:
                    logger.info(f"第 {attempt} 次重试（共 {max_retries} 次）...")

            def _fetch_via_adapter() -> pd.DataFrame:
                """Fetch each ticker via the adapter; return a wide Close frame.

                The macro tickers (QQQ/GLD/BTC-USD/000300.SS) are US-style —
                ``000300.SS`` is already in yfinance-native form, and the
                adapter's ``_to_yf_ticker`` passes it through unchanged
                (only ``.SH`` is remapped to ``.SS``). All four use
                ``market="us"`` so the adapter treats them as US tickers.
                """
                # Macro tickers are yfinance-US-style (incl. 000300.SS which
                # yfinance accepts natively as a Shanghai ADR). Using
                # ``market="us"`` avoids the adapter's .SH→.SS remap, which is
                # a no-op for these symbols anyway.
                adapter = YFinanceDataSource(
                    max_retries=max_retries,
                    retry_delay=retry_delay,
                )
                adapter.connect()

                per_ticker_close: dict[str, pd.Series] = {}
                for ticker in tickers:
                    long_df = adapter.download_kline(
                        ticker, market="us", count=fetch_days
                    )
                    if long_df is None or long_df.empty:
                        logger.warning(
                            "适配器未返回 %s 的数据（可能限速或代码无效）", ticker
                        )
                        continue
                    # Long → Close Series indexed by trading date.
                    # ``_normalize`` sorts ascending by date; reuse that order.
                    close_series = pd.Series(
                        long_df["close"].to_numpy(),
                        index=pd.to_datetime(long_df["date"]),
                        name=ticker,
                    )
                    per_ticker_close[ticker] = close_series

                if not per_ticker_close:
                    return pd.DataFrame()

                # Outer-join on a common DatetimeIndex to preserve each
                # ticker's own trading calendar (BTC trades weekends; QQQ/GLD
                # do not). This reproduces the alignment that the original
                # ``yf.download(tickers=[...])`` single round-trip produced —
                # a unioned calendar with NaN where a ticker had no bar.
                wide = pd.DataFrame(per_ticker_close)
                wide.index.name = "Date"
                return wide

            data = fetch_with_retry(
                _fetch_via_adapter,
                max_retries=max_retries,
                retry_delay=retry_delay,
                # The original macro loop catches EVERY exception and retries
                # it (just with different log levels) — preserve that exact
                # behavior. ``is_rate_limited`` is consulted only for log
                # surfacing inside ``_on_retry``.
                is_retryable=lambda _exc: True,
                on_retry=_on_retry,
                label="macro.fetch_combined_data",
            )

            if data is None or data.empty:
                logger.error("下载的数据为空")
                return None

            # 数据清洗：对齐到股票交易日（以科技股代理资产为基准）。
            # 保留 ``tickers`` 声明顺序作为列顺序（strategist 遍历
            # ``data.columns`` 时不依赖顺序，但保持确定性有助于日志/调试）。
            tech_col = str(self.config.tech_proxy)
            data = data.dropna(subset=[tech_col])  # type: ignore
            # 填充其他资产可能缺失的数据（如加密货币在交易日可能缺失）
            data = data.ffill()
            # 丢弃仍包含 NaN 的行（例如首行数据缺失）
            data = data.dropna()

            # 恢复 ``tickers`` 声明顺序（outer-join 按字典插入顺序保留，
            # 但 ffill/dropna 不应改变列序；显式 reindex 以防回归）。
            present_cols = [t for t in tickers if t in data.columns]
            data = data[present_cols]

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
            - flat / zero-variance 序列或长度不足时返回 0.0（不会返回 NaN）

        Parity: mirrors ``MomentumRanker.calculate_rsrs``
        (``src/micro/momentum_scanner.py:47-79``); the canonical Module #5
        implementation is authoritative — see S002-001/S002-002 and
        ``design/cdd/micro-momentum-scanner.md`` §4.1. This macro copy is a
        delegated duplicate that MUST stay in guard-parity with Module #5; the
        parity battery in ``tests/unit/macro/test_data_loader_rsrs.py`` is the
        regression guard. Sign convention: zero slope -> +1 (unified under
        S002-001 / OQ-11).
        """
        if len(prices) < window:
            return 0.0

        y = prices.iloc[-window:].values
        x = np.arange(len(y))

        # 零方差 (flat) 保护：linregress 在 y 无方差时返回 rvalue=nan，
        # 会导致趋势强度为 nan 并污染 strategist 提示词。与 Module #5 一致。
        if float(np.var(y)) <= 1e-10:
            return 0.0

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # 将 R2 * Slope 符号作为趋势强度
        # R² (0~1) 代表趋势的纯度，乘以 slope 的符号 (+1/-1)
        # 符号约定 (S002-001 统一)：零斜率 -> +1，与 Module #5 标量路径一致。
        trend_strength = (r_value ** 2) * (1 if slope >= 0 else -1)
        # 防御：即使经过方差检查，极端输入仍可能产生 nan。
        return 0.0 if trend_strength != trend_strength else trend_strength

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
                    # 防御性强制：即使 calculate_rsrs 的守卫被绕过，
                    # NaN 也永远不会进入 strategist 提示词 (S002-002)。
                    metrics[f'{col}_rsrs'] = float(rsrs_val) if rsrs_val == rsrs_val else 0.0

            logger.info(f"📊 指标计算完成 (Days={len(data)})")
            return metrics
        except Exception as e:
            logger.error(f"指标计算错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}