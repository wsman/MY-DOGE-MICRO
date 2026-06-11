import pandas as pd
import os
import sys
from datetime import datetime
from collections import Counter
from scipy import stats
import numpy as np

# S002-005 (TR-011): the module-global ``current_dir`` / ``project_root`` /
# ``data_dir`` path recalculations (forbidden ``_PROJECT_ROOT`` pattern under
# ADR-0001) are removed. Paths now resolve through the centralized settings
# singleton (``doge.config.get_settings``), and raw sqlite3 module connect is
# replaced by the clean ``SQLiteConnection`` adapter. ``project_root`` is kept
# ONLY as a derived settings-backed value for the legacy CSV-output path so the
# standalone CLI entrypoint (``if __name__ == "__main__"``) keeps working.
try:
    from doge.config import get_settings

    def _project_root():
        return str(get_settings().project_root)

    def _db_path_for(db_name):
        """Resolve a market DB filename to an absolute path via settings.

        ``db_name`` is a bare filename like ``market_data_cn.db``; the data dir
        comes from ``Settings().db.dir`` (overridable via ``DOGE_DB_DIR``).
        """
        return os.path.join(str(get_settings().db.dir), db_name)
except ImportError:  # pragma: no cover - legacy bootstrap fallback
    def _project_root():
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _db_path_for(db_name):
        return os.path.join(_project_root(), "data", db_name)


def _build_sqlite_connection(db_path):
    """Build a clean ``SQLiteConnection`` adapter for ``db_path``.

    The adapter (not a raw sqlite3 module connect) owns the connection lifecycle.
    Imported lazily so this module is import-safe; the doge package is the
    production path (the editable install / ``pythonpath=['src']`` makes
    ``doge.infrastructure`` importable everywhere this module runs).
    """
    from doge.infrastructure.database.sqlite import SQLiteConnection

    return SQLiteConnection(db_path)


class MomentumRanker:
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self):
        """Build the scanner config as a dict VIEW over ``get_settings().market``.

        S002-008 (TR-019): ``Settings().market`` is now the single source of
        truth for scanner filters (ADR-0002). This method no longer opens
        ``models_config.json`` nor reads a ``scanner_filters`` block — that
        block was removed from both the live config and the tracked template,
        and a drift guard (``tests/contract/test_scanner_filter_drift_guard.py``)
        fails if any production module reintroduces the key-read.

        The returned dict preserves the LEGACY key names used at the call sites
        (``analyze_market`` reads ``us_blacklist`` / ``rsrs_window`` /
        ``max_change_pct`` via ``self.config.get(...)``, momentum_scanner.py
        ~214-216). The mapping is:
          - ``MarketConfig.us_blacklist`` (tuple)  -> ``us_blacklist`` (list)
          - ``MarketConfig.cn_min_volume``         -> ``min_volume_cn``
          - ``MarketConfig.us_min_volume``         -> ``min_volume_us``
          - ``MarketConfig.max_change_pct``        -> ``max_change_pct``
          - ``MarketConfig.rsrs_window``           -> ``rsrs_window``
          - ``MarketConfig.cn_universe_prefixes``  -> ``cn_universe_prefixes``
        """
        market = get_settings().market
        return {
            "us_blacklist": list(market.us_blacklist),
            "min_volume_cn": market.cn_min_volume,
            "min_volume_us": market.us_min_volume,
            "max_change_pct": market.max_change_pct,
            "rsrs_window": market.rsrs_window,
            "cn_universe_prefixes": list(market.cn_universe_prefixes),
        }

    def calculate_rsrs(self, series, window=18):
        """
        计算趋势强度 (RSRS 替代指标)
        返回: -1.0 ~ 1.0 (R2 * Sign(Slope))
        """
        try:
            if len(series) < window:
                return 0.0
            
            # 取最近 window 天的数据
            y = series.iloc[-window:].values
            x = np.arange(len(y))

            # 零方差 (flat) 保护：linregress 在 y 无方差时返回 rvalue=nan，
            # 会导致趋势强度为 nan。向量化路径 (_calculate_rsrs_vectorized)
            # 通过 y_var > 1e-10 保护此情形并返回 0.0；此处与之一致，
            # 保证标量与向量化两条路径在 flat 输入上行为相同 (BUG E)。
            if float(np.var(y)) <= 1e-10:
                return 0.0

            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

            # R2 * Slope符号
            # 显式转换类型以消除 Pylance 警告
            r_sq = float(r_value) ** 2
            # Sign convention (S002-001, OQ-11/TR-016 RESOLVED): zero slope -> +1,
            # unifying the scalar path with the vectorized path (np.where below)
            # and the DuckDB-SQL view (CASE WHEN ... >= 0 THEN 1). See the
            # cross-implementation parity test tests/unit/momentum/test_rsrs_parity.py.
            sign = 1.0 if float(slope) >= 0 else -1.0

            trend_strength = r_sq * sign
            # 防御：即使经过方差检查，极端输入仍可能产生 nan。
            return 0.0 if trend_strength != trend_strength else trend_strength
        except Exception as e:
            # print(f"[WARN] RSRS计算异常: {e}")
            return 0.0

    def _calculate_rsrs_vectorized(self, price_matrix):
        """
        向量化计算 RSRS
        Args:
            price_matrix: numpy array, shape (N_stocks, window_size)
        Returns:
            rsrs_values: numpy array, shape (N_stocks,)
        """
        if price_matrix.size == 0:
            return np.array([])

        N, T = price_matrix.shape

        # 1. 准备 X (时间序列 0, 1, ..., T-1)
        x = np.arange(T)
        x_mean = x.mean()
        x_dev = x - x_mean             # Shape: (T,)
        x_var = np.sum(x_dev ** 2)     # Scalar (分母部分)

        # 2. 准备 Y (价格序列)
        y_mean = np.mean(price_matrix, axis=1, keepdims=True)
        y_dev = price_matrix - y_mean  # Shape: (N, T)

        # 3. 计算 Slope (斜率)
        # Cov(x, y) = sum(x_dev * y_dev)
        cov_xy = np.dot(y_dev, x_dev)  # Shape: (N,)
        slope = cov_xy / x_var

        # 4. 计算 R^2 (决定系数)
        # R^2 = (Cov(x,y)^2) / (Var(x) * Var(y))
        y_var = np.sum(y_dev ** 2, axis=1) # Shape: (N,)

        # 处理 y_var 为 0 的情况 (价格完全不变)，避免除零错误
        valid_mask = y_var > 1e-10
        r_sq = np.zeros(N)

        # 仅对有效数据计算
        r_sq[valid_mask] = (cov_xy[valid_mask] ** 2) / (x_var * y_var[valid_mask])

        # 5. 计算 RSRS = R^2 * Sign(Slope)
        # Sign convention (S002-001, OQ-11/TR-016 RESOLVED): zero slope -> +1 to
        # match the scalar path (sign = 1.0 if slope >= 0 else -1.0 above) and
        # the DuckDB-SQL view (CASE WHEN ... >= 0 THEN 1). np.where broadcasts
        # over the (N,) slope array; a Python scalar conditional would break.
        rsrs = r_sq * np.where(slope >= 0, 1.0, -1.0)

        return rsrs

    def test_rsrs_accuracy(self):
        """自检函数：对比向量化与Scipy的结果"""
        print("[TEST] 正在执行算法一致性自检...")
        # 生成随机测试数据
        np.random.seed(42)
        test_data = np.random.rand(100, 18) * 100  # 100只股票，18天数据

        # 1. 向量化计算
        vec_res = self._calculate_rsrs_vectorized(test_data)

        # 2. 循环计算 (使用旧方法)
        loop_res = []
        for row in test_data:
            loop_res.append(self.calculate_rsrs(pd.Series(row)))

        # 3. 对比
        diff = np.abs(vec_res - np.array(loop_res))
        max_diff = diff.max()

        if max_diff < 1e-6:
            print("[OK] 算法验证通过！误差极小。")
        else:
            print(f"[ERR] 算法存在差异，最大误差: {max_diff}")
        return max_diff

    def get_connection(self, db_name):
        """Build a clean ``SQLiteConnection`` adapter for ``db_name``.

        Returns ``None`` (and prints ``[ERR]``) when the resolved DB file does
        not exist, preserving the legacy behavior contract relied on by
        :meth:`analyze_market`. The path is resolved via centralized settings
        (``Settings().db.dir``), NOT a module-global ``data_dir`` recalculation.
        The adapter (not a raw sqlite3 module connect) owns the actual connection
        lifecycle — callers use ``with adapter.connect() as conn:`` (S002-005).
        """
        db_path = _db_path_for(db_name)
        if not os.path.exists(db_path):
            print(f"[ERR] 数据库不存在: {db_path}")
            return None
        return _build_sqlite_connection(db_path)

    def analyze_market(self, market_type, db_name, amount_threshold):
        print(f"\n[GO] 正在分析 {market_type} 市场动量...")

        # 1. 优先使用传入参数，否则使用配置
        min_vol = amount_threshold  # 保留原参数，不做覆盖逻辑，以保持兼容
        blacklist = set(self.config.get('us_blacklist', []))
        window = self.config.get('rsrs_window', 18)
        max_change_pct = self.config.get('max_change_pct', 400)
        # S002-008: CN investable-code prefixes are now sourced from
        # Settings().market.cn_universe_prefixes via _load_config (canonical),
        # not hardcoded inline.
        cn_prefixes = tuple(self.config.get('cn_universe_prefixes', ('00', '30', '60', '68')))

        print(f"   [CFG] 筛选标准: 60日涨幅排名 | 60日日均成交额 > {min_vol/10000:.0f}万")

        adapter = self.get_connection(db_name)
        if not adapter:
            return

        # S002-005: the adapter owns the connection lifecycle via its
        # ``connect()`` contextmanager (replaces raw sqlite3 module connect +
        # manual ``conn.close()``). The yielded object is still a
        # ``sqlite3.Connection``, so ``pd.read_sql_query`` works unchanged.
        try:
            with adapter.connect() as conn:
                # 获取最新日期
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(date) FROM stock_prices")
                max_date = cursor.fetchone()[0]
                if not max_date:
                    print("[WARN] 数据库为空")
                    return

                # 加载最近半年数据
                print("[WAIT] 正在加载数据到内存...")
                query = f"""
                    SELECT ticker, date, close, high, low, amount
                    FROM stock_prices
                    WHERE date >= date('{max_date}', '-180 days')
                    ORDER BY ticker, date ASC
                """
                df = pd.read_sql_query(query, conn)
        except Exception as e:
            print(f"[ERR] 读取错误: {e}")
            return

        if df.empty:
            print("[WARN] 无数据")
            return

        print(f"[INFO] 数据加载完成，开始筛选 {len(df['ticker'].unique())} 只股票...")
        
        # --- 批处理容器 ---
        candidates_meta = []   # 存储元数据 (ticker, price, vol, etc.)
        candidates_prices = [] # 存储价格序列 (用于向量化计算)
        global_start_dates = []
        global_end_dates = []

        grouped = df.groupby('ticker')

        for ticker, group in grouped:
            if len(group) < 61: continue  # 确保有足够数据计算 60日涨幅
            
            # --- 过滤器逻辑 (从配置读取) ---
            if market_type == 'US':
                if ticker in blacklist: continue
                # 过滤常见的 warrant (权证) 或异类后缀 (5字符以上通常要注意)
                ticker_str = str(ticker)
                if len(ticker_str) > 4 and ticker_str not in ['GOOGL', 'BRK.B']: 
                    # 简单启发式：美股正股代码通常 <= 4 位 (除了个别)
                    # YieldMax 很多是 4 位，所以必须靠 blacklist
                    pass

            if market_type == 'CN':
                # 确保 ticker 是字符串
                ticker_str = str(ticker)
                raw_code = ticker_str.split('.')[0]
                if not raw_code.startswith(cn_prefixes): continue
            
            # --- 流动性过滤 ---
            avg_amt = group['amount'].tail(60).mean()
            if avg_amt < min_vol: continue

            # --- 涨跌幅计算 ---
            curr_row = group.iloc[-1]
            prev_row = group.iloc[-61]
            p_curr = curr_row['close']
            p_prev = prev_row['close']
            if p_prev == 0: continue
            
            change_pct = (p_curr - p_prev) / p_prev * 100
            
            # 虚假暴涨熔断过滤
            if market_type == 'US' and change_pct > max_change_pct:
                continue
                
            # [OK] 关键改动: 此时不计算 RSRS，只收集数据
            # 获取最近 window 天的收盘价
            recent_prices = group['close'].values[-window:]
            
            # 如果数据不足 window 天 (虽然前面检查了61天，但以防万一)，补0或跳过
            if len(recent_prices) < window:
                continue

            candidates_prices.append(recent_prices)
            candidates_meta.append({
                'ticker': ticker,
                'price_60d_ago': round(p_prev, 2),
                'price_current': round(p_curr, 2),
                'change_percent': round(change_pct, 2),
                'avg_daily_volume': round(avg_amt, 0),
                'start_date': prev_row['date'],
                'end_date': curr_row['date']
            })
            
            global_start_dates.append(prev_row['date'])
            global_end_dates.append(curr_row['date'])

        # --- 向量化计算阶段 ---
        if not candidates_meta:
            print("[WARN] 没有符合条件的标的")
            return

        print(f"[FAST] 正在对 {len(candidates_meta)} 只优选股票进行 RSRS 向量化计算...")

        # 转换为 numpy 矩阵 (N, window)
        price_matrix = np.array(candidates_prices)

        # [GO] 一次性计算所有 RSRS
        rsrs_scores = self._calculate_rsrs_vectorized(price_matrix)

        # 将结果合并回元数据
        for i, meta in enumerate(candidates_meta):
            meta['rsrs_z'] = round(rsrs_scores[i], 2)
            
        # --- 后续输出逻辑 ---
        results = pd.DataFrame(candidates_meta)
        results.sort_values('change_percent', ascending=False, inplace=True)
        top_200 = results.head(200)
        
        # 文件名日期逻辑优化
        # End Date: 取最大值 (最新日期)
        # Start Date: 取众数 (绝大多数股票的起始日期)，过滤停牌股干扰
        if global_end_dates:
            file_end = max(global_end_dates).replace('-', '')
        else:
            file_end = datetime.now().strftime('%Y%m%d')
            
        if global_start_dates:
            # 获取出现次数最多的日期 (Mode)
            most_common_start = Counter(global_start_dates).most_common(1)[0][0]
            file_start = most_common_start.replace('-', '')
        else:
            file_start = "00000000"
        
        filename = f"Top200_Momentum_{market_type}_{file_start}-{file_end}.csv"
        save_path = os.path.join(_project_root(), filename)
        
        output_cols = ['ticker', 'price_60d_ago', 'price_current', 'change_percent', 'avg_daily_volume', 'rsrs_z']
        top_200[output_cols].to_csv(save_path, index=False)
        
        print(f"[OK] {market_type} 榜单已生成: {filename}")
        print(f"   #1 榜首: {top_200.iloc[0]['ticker']} (+{top_200.iloc[0]['change_percent']}%) | RSRS: {top_200.iloc[0]['rsrs_z']}")

def main():
    ranker = MomentumRanker()

    # S002-008 (TR-019): amount thresholds now come from Settings().market
    # (the single source of truth) instead of hardcoded 2e8 / 2e7 literals,
    # closing the call-site-override gap noted in the CDD §7 / §9 open-questions.
    market = get_settings().market

    # A股 (A股最低日均成交额阈值, 默认 2亿 RMB)
    ranker.analyze_market('CN', 'market_data_cn.db', market.cn_min_volume)

    # 美股 (美股最低日均成交额阈值, 默认 2000万 USD)
    ranker.analyze_market('US', 'market_data_us.db', market.us_min_volume)

if __name__ == "__main__":
    main()
