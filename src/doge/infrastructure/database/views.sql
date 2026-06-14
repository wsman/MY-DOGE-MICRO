-- ============================================================================
-- DuckDB 分析视图定义 (CANONICAL, VERSION-CONTROLLED)
-- ----------------------------------------------------------------------------
-- This file is the SINGLE SOURCE OF TRUTH for the DuckDB analytical-view DDL.
-- It is shipped under version control at:
--   src/doge/infrastructure/database/views.sql
-- and is consumed by the clean-arch refresh path
-- (``DuckDBConnection.refresh_views``) and the legacy ``ai_analysis.run_views_sql``
-- loader. A mirror copy lives at ``data/views.sql`` for backward compatibility
-- with the ``duckdb data/market.duckdb < data/views.sql`` CLI invocation; the
-- tracked file here is canonical.
--
-- Usage:
--   python src/ai_analysis/catalog_generator.py
--   duckdb data/market.duckdb < data/views.sql   (legacy CLI mirror)
--
-- S003-005 / SIGN-INVERSION FIX:
--   The two RSRS views (``vw_rsrs_ranking_cn`` / ``vw_rsrs_ranking_us``) now
--   define the per-ticker regression time index as
--     ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date ASC) AS rn_asc
--   and feed ``REGR_SLOPE(rn_asc, close)`` / ``REGR_R2(rn_asc, close)`` so that
--   rn_asc=1 is the OLDEST bar in the window. This matches the canonical Python
--   path (``micro.momentum_scanner.MomentumRanker`` uses
--   ``x = np.arange(len(y))`` oldest -> newest, regressing close on time), so a
--   perfectly increasing 18-bar window now yields RSRS = +1.0 from BOTH the view
--   and the Python scalar/vectorized paths (cross-implementation parity, S002-001
--   intent finally satisfied). Previously the regression used
--   ``ROW_NUMBER() OVER (... ORDER BY date DESC) AS rn`` (rn=1 = newest), which
--   inverted the regression sign for every monotonic series. The downstream
--   liquidity / 60-day-change CTEs that depend on the "rn=1=newest" convention
--   keep using the original ``rn``; only the regression's time index changed.
--   Regression guard: ``tests/migration/test_rsrs_view_sign_convention.py``.
-- ============================================================================
--
-- RETENTION INVARIANT (TR-006 / ADR-0003):
--   The widest analytical-view window in this file is 730 days
--   (vw_market_breadth_cn, INTERVAL 730 DAYS). The per-ticker destructive
--   prune applied on every OHLCV write — save_stock_data_custom ->
--   Settings().market.retention_days -> DOGE_RETENTION_DAYS (default 730) —
--   MUST be >= 730 so breadth scans never see silently-truncated rows.
--   Regression guard: tests/migration/test_retention_view_window_safety.py
--   asserts max(INTERVAL N DAYS) <= retention_days.
-- ============================================================================

-- 连接 SQLite 数据源（只读，零拷贝）
ATTACH IF NOT EXISTS 'data/market_data_cn.db' AS cn (TYPE sqlite);
ATTACH IF NOT EXISTS 'data/market_data_us.db' AS us (TYPE sqlite);

-- ============================================================================
-- View 1: 市场宽度 -- 每日涨跌家数、涨跌幅分布
-- ============================================================================
CREATE OR REPLACE VIEW vw_market_breadth_cn AS
WITH daily_return AS (
    SELECT
        ticker,
        date,
        close,
        LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close,
    FROM cn.stock_prices
    WHERE CAST(date AS DATE) >= (SELECT MAX(CAST(date AS DATE)) FROM cn.stock_prices) - INTERVAL 730 DAYS
),
classified AS (
    SELECT
        date,
        CASE
            WHEN close > prev_close AND prev_close IS NOT NULL THEN 'up'
            WHEN close < prev_close AND prev_close IS NOT NULL THEN 'down'
            WHEN close = prev_close AND prev_close IS NOT NULL THEN 'flat'
            ELSE NULL
        END AS direction,
        ((close - prev_close) / NULLIF(prev_close, 0)) * 100 AS return_pct,
    FROM daily_return
)
SELECT
    date,
    COUNT(*) FILTER (WHERE direction = 'up')       AS advancers,
    COUNT(*) FILTER (WHERE direction = 'down')     AS decliners,
    COUNT(*) FILTER (WHERE direction = 'flat')     AS unchanged,
    COUNT(*) FILTER (WHERE direction IS NOT NULL)  AS active,
    ROUND(AVG(return_pct) FILTER (WHERE direction IS NOT NULL), 4) AS avg_return_pct,
    ROUND(STDDEV_POP(return_pct) FILTER (WHERE direction IS NOT NULL), 4) AS std_return_pct,
    ROUND(
        COUNT(*) FILTER (WHERE direction = 'up') * 100.0 /
        NULLIF(COUNT(*) FILTER (WHERE direction IS NOT NULL), 0), 2
    ) AS advance_ratio,
FROM classified
GROUP BY date
ORDER BY date DESC;

-- ============================================================================
-- View 2: RSRS 动量排名 (先按 60 日涨幅取 Top 200，再计算 18 日 RSRS)
-- 与 momentum_scanner.py 原始算法对齐：
--   1) 180 天数据 >= 61 个交易日
--   2) 20 日均量 > 50 万
--   3) 按 60 日涨幅 (close[-1] vs close[-61]) 取 Top 200
--   4) 对 Top 200 用最近 18 天收盘价做时间回归，RSRS = R2 * sign(slope)
--   5) 最终按 RSRS 降序排列
-- SIGN CONVENTION (S003-005): the regression time index ``rn_asc`` is ASC
--   (rn_asc=1=oldest) so the slope matches Python's price-on-time path. The
--   liquidity / 60-day-change CTEs keep the legacy ``rn`` (DESC, rn=1=newest).
-- ============================================================================
CREATE OR REPLACE VIEW vw_rsrs_ranking_cn AS
WITH recent AS (
    SELECT
        ticker,
        date,
        close,
        volume,
        amount,
        ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn,
        ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date ASC)  AS rn_asc,
    FROM cn.stock_prices
    WHERE CAST(date AS DATE) >= (SELECT MAX(CAST(date AS DATE)) FROM cn.stock_prices) - INTERVAL 180 DAYS
      -- 仅保留 A 股主板/创业板/科创板 (与 momentum_scanner.py 一致)
      AND regexp_matches(
            split_part(ticker, '.', 1),
            '^(00|30|60|68)'
          )
),
-- Step 1: 计算 60 日涨幅 & 流动性指标 (uses DESC rn — rn=1 is newest)
change_60d AS (
    SELECT
        ticker,
        FIRST(close ORDER BY rn)                              AS last_close,
        MAX(close) FILTER (WHERE rn = 61)                     AS close_60d_ago,
        ROUND(
            ((FIRST(close ORDER BY rn)
              - MAX(close) FILTER (WHERE rn = 61))
             / NULLIF(MAX(close) FILTER (WHERE rn = 61), 0))
            * 100, 2
        )                                                     AS pct_change_60d,
        CAST(AVG(volume) FILTER (WHERE rn <= 20) AS BIGINT)   AS avg_vol_20d,
        AVG(amount) FILTER (WHERE rn <= 60)                   AS avg_amt_60d,
        COUNT(*)                                              AS data_points,
    FROM recent
    GROUP BY ticker
    HAVING COUNT(*) >= 61
),
-- Step 2: 按 60 日涨幅取 Top 200（过滤流动性）
momentum_top AS (
    SELECT *
    FROM change_60d
    WHERE avg_vol_20d > 500000
      AND last_close IS NOT NULL
    ORDER BY pct_change_60d DESC
    LIMIT 200
),
-- Step 3: 对 Top 200 计算 18 日 RSRS (uses ASC rn_asc — oldest first, matches Python)
windowed AS (
    SELECT r.*
    FROM recent r
    JOIN momentum_top m ON r.ticker = m.ticker
    WHERE r.rn <= 18
),
regression AS (
    SELECT
        ticker,
        COALESCE(REGR_R2(rn_asc, close), 0) *
        CASE WHEN COALESCE(REGR_SLOPE(rn_asc, close), 0) >= 0 THEN 1 ELSE -1 END AS rsrs,
        COUNT(*) AS rsrs_points,
    FROM windowed
    GROUP BY ticker
    HAVING COUNT(*) >= 10
)
-- Step 4: 最终输出（按 RSRS 排序）
SELECT
    m.ticker,
    ROUND(m.last_close, 2)        AS last_close,
    ROUND(m.close_60d_ago, 2)     AS close_60d_ago,
    m.pct_change_60d,
    m.avg_vol_20d,
    ROUND(m.avg_amt_60d / 10000, 2) AS avg_amt_60d_wan,
    ROUND(r.rsrs, 6)              AS rsrs,
    r.rsrs_points,
    DENSE_RANK() OVER (ORDER BY r.rsrs DESC) AS rank,
FROM momentum_top m
JOIN regression r ON m.ticker = r.ticker
ORDER BY r.rsrs DESC;

-- ============================================================================
-- View 3: 成交量异常检测 (当日成交量 vs 20 日均量)
-- ============================================================================
CREATE OR REPLACE VIEW vw_volume_anomalies_cn AS
WITH vol_ratio AS (
    SELECT
        ticker,
        date,
        volume,
        close,
        open,
        AVG(volume) OVER (
            PARTITION BY ticker
            ORDER BY date
            ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
        ) AS avg_vol_20d,
        (close - open) / NULLIF(open, 0) * 100 AS intraday_return,
    FROM cn.stock_prices
    WHERE CAST(date AS DATE) >= '2025-01-01'  -- wide window for anomaly baseline
),
anomalous AS (
    SELECT
        ticker,
        date,
        volume,
        ROUND(avg_vol_20d, 0) AS avg_vol_20d,
        ROUND(volume / NULLIF(avg_vol_20d, 0), 2) AS vol_ratio,
        ROUND(intraday_return, 2) AS intraday_return,
    FROM vol_ratio
    WHERE avg_vol_20d > 0
)
SELECT *
FROM anomalous
WHERE vol_ratio >= 2.0
ORDER BY date DESC, vol_ratio DESC;

-- ============================================================================
-- View 4: 市场截面收益率分布 (按日期查看全市场收益率分布)
-- ============================================================================
CREATE OR REPLACE VIEW vw_cross_sectional_return_cn AS
WITH daily_return AS (
    SELECT
        ticker,
        date,
        close,
        LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close,
        volume,
    FROM cn.stock_prices
)
SELECT
    ticker,
    date,
    ROUND(((close - prev_close) / NULLIF(prev_close, 0)) * 100, 4) AS return_pct,
    volume,
    close,
FROM daily_return
WHERE prev_close IS NOT NULL
    AND CAST(date AS DATE) >= (SELECT MAX(CAST(date AS DATE)) FROM cn.stock_prices) - INTERVAL 365 DAYS
ORDER BY date DESC, ticker;

-- ============================================================================
-- View 5: 个股日度数据宽表 (含涨跌幅、均线、ATR 等衍生指标)
-- ============================================================================
CREATE OR REPLACE VIEW vw_daily_enriched_cn AS
WITH base AS (
    -- 预计算 LAG 值，避免窗口函数嵌套
    SELECT
        ticker,
        date,
        open,
        high,
        low,
        close,
        volume,
        amount,
        LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close,
    FROM cn.stock_prices
    WHERE CAST(date AS DATE) >= (SELECT MAX(CAST(date AS DATE)) FROM cn.stock_prices) - INTERVAL 365 DAYS
)
SELECT
    ticker,
    date,
    open,
    high,
    low,
    close,
    volume,
    amount,
    -- 涨跌幅
    ROUND(((close - prev_close) / NULLIF(prev_close, 0)) * 100, 4) AS return_pct,
    -- 5/10/20/60 日均线
    ROUND(AVG(close) OVER w5, 2) AS ma_5,
    ROUND(AVG(close) OVER w10, 2) AS ma_10,
    ROUND(AVG(close) OVER w20, 2) AS ma_20,
    ROUND(AVG(close) OVER w60, 2) AS ma_60,
    -- ATR (14)
    ROUND(AVG(
        GREATEST(high - low, ABS(high - prev_close), ABS(low - prev_close))
    ) OVER w_atr, 4) AS atr_14,
    -- 距 60 日均线偏离度
    ROUND(((close - AVG(close) OVER w60) /
           NULLIF(AVG(close) OVER w60, 0)) * 100, 2) AS ma60_deviation,
    -- 20 日波动率
    ROUND(STDDEV_SAMP(
        ((close - prev_close) / NULLIF(prev_close, 0)) * 100
    ) OVER w_vol, 4) AS volatility_20d,
FROM base
WHERE prev_close IS NOT NULL
WINDOW
    w5   AS (PARTITION BY ticker ORDER BY date ROWS BETWEEN  4 PRECEDING AND CURRENT ROW),
    w10  AS (PARTITION BY ticker ORDER BY date ROWS BETWEEN  9 PRECEDING AND CURRENT ROW),
    w20  AS (PARTITION BY ticker ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
    w60  AS (PARTITION BY ticker ORDER BY date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW),
    w_atr AS (PARTITION BY ticker ORDER BY date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW),
    w_vol AS (PARTITION BY ticker ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW);

-- ============================================================================
-- View 6: 美股市场宽度
-- ============================================================================
CREATE OR REPLACE VIEW vw_market_breadth_us AS
WITH daily_return AS (
    SELECT
        ticker,
        date,
        close,
        LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close,
    FROM us.stock_prices
    WHERE CAST(date AS DATE) >= (SELECT MAX(CAST(date AS DATE)) FROM us.stock_prices) - INTERVAL 365 DAYS
),
classified AS (
    SELECT
        date,
        CASE
            WHEN close > prev_close AND prev_close IS NOT NULL THEN 'up'
            WHEN close < prev_close AND prev_close IS NOT NULL THEN 'down'
            WHEN close = prev_close AND prev_close IS NOT NULL THEN 'flat'
            ELSE NULL
        END AS direction,
        ((close - prev_close) / NULLIF(prev_close, 0)) * 100 AS return_pct,
    FROM daily_return
)
SELECT
    date,
    COUNT(*) FILTER (WHERE direction = 'up')       AS advancers,
    COUNT(*) FILTER (WHERE direction = 'down')     AS decliners,
    COUNT(*) FILTER (WHERE direction = 'flat')     AS unchanged,
    COUNT(*) FILTER (WHERE direction IS NOT NULL)  AS active,
    ROUND(AVG(return_pct) FILTER (WHERE direction IS NOT NULL), 4) AS avg_return_pct,
    ROUND(STDDEV_POP(return_pct) FILTER (WHERE direction IS NOT NULL), 4) AS std_return_pct,
FROM classified
GROUP BY date
ORDER BY date DESC;

-- ============================================================================
-- View 7: 美股 RSRS 排名 (先按 60 日涨幅取 Top 200，再计算 18 日 RSRS)
-- SIGN CONVENTION (S003-005): the regression time index ``rn_asc`` is ASC
--   (rn_asc=1=oldest) so the slope matches Python's price-on-time path. The
--   liquidity / 60-day-change CTEs keep the legacy ``rn`` (DESC, rn=1=newest).
-- ============================================================================
CREATE OR REPLACE VIEW vw_rsrs_ranking_us AS
WITH recent AS (
    SELECT
        ticker,
        date,
        close,
        volume,
        amount,
        ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn,
        ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date ASC)  AS rn_asc,
    FROM us.stock_prices
    WHERE CAST(date AS DATE) >= (SELECT MAX(CAST(date AS DATE)) FROM us.stock_prices) - INTERVAL 180 DAYS
),
-- Step 1: 计算 60 日涨幅 & 流动性 (uses DESC rn — rn=1 is newest)
change_60d AS (
    SELECT
        ticker,
        FIRST(close ORDER BY rn)                              AS last_close,
        MAX(close) FILTER (WHERE rn = 61)                     AS close_60d_ago,
        ROUND(
            ((FIRST(close ORDER BY rn)
              - MAX(close) FILTER (WHERE rn = 61))
             / NULLIF(MAX(close) FILTER (WHERE rn = 61), 0))
            * 100, 2
        )                                                     AS pct_change_60d,
        CAST(AVG(volume) FILTER (WHERE rn <= 20) AS BIGINT)   AS avg_vol_20d,
        AVG(amount) FILTER (WHERE rn <= 60)                   AS avg_amt_60d,
        COUNT(*)                                              AS data_points,
    FROM recent
    GROUP BY ticker
    HAVING COUNT(*) >= 61
),
-- Step 2: 按 60 日涨幅取 Top 200（美股流动性门槛 50,000 股）
momentum_top AS (
    SELECT *
    FROM change_60d
    WHERE avg_vol_20d > 50000
      AND last_close IS NOT NULL
    ORDER BY pct_change_60d DESC
    LIMIT 200
),
-- Step 3: 对 Top 200 计算 18 日 RSRS (uses ASC rn_asc — oldest first, matches Python)
windowed AS (
    SELECT r.*
    FROM recent r
    JOIN momentum_top m ON r.ticker = m.ticker
    WHERE r.rn <= 18
),
regression AS (
    SELECT
        ticker,
        COALESCE(REGR_R2(rn_asc, close), 0) *
        CASE WHEN COALESCE(REGR_SLOPE(rn_asc, close), 0) >= 0 THEN 1 ELSE -1 END AS rsrs,
        COUNT(*) AS rsrs_points,
    FROM windowed
    GROUP BY ticker
    HAVING COUNT(*) >= 10
)
-- Step 4: 最终输出（按 RSRS 排序）
SELECT
    m.ticker,
    ROUND(m.last_close, 2)        AS last_close,
    ROUND(m.close_60d_ago, 2)     AS close_60d_ago,
    m.pct_change_60d,
    m.avg_vol_20d,
    ROUND(m.avg_amt_60d / 10000, 2) AS avg_amt_60d_wan,
    ROUND(r.rsrs, 6)              AS rsrs,
    r.rsrs_points,
    DENSE_RANK() OVER (ORDER BY r.rsrs DESC) AS rank,
FROM momentum_top m
JOIN regression r ON m.ticker = r.ticker
ORDER BY r.rsrs DESC;
