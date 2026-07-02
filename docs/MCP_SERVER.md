# doge-db MCP 服务器

doge-db 是 MY-DOGE 量化系统的 MCP (Model Context Protocol) 数据服务层，通过 DuckDB 零拷贝读取本地 SQLite 数据库，为 Claude Code 和其他 MCP 客户端提供 A 股/美股行情查询、RSRS 动量排名、市场宽度分析、成交量异动检测等 6 个工具。

## 目录

- [快速开始](#快速开始)
- [部署模式](#部署模式)
- [工具清单](#工具清单)
  - [query_stock](#query_stock)
  - [stock_overview](#stock_overview)
  - [rsrs_ranking](#rsrs_ranking)
  - [market_breadth](#market_breadth)
  - [volume_anomalies](#volume_anomalies)
  - [list_views](#list_views)
- [数据库视图](#数据库视图)
- [数据源](#数据源)
- [SSE 模式 HTTP 接口](#sse-模式-http-接口)
- [配置](#配置)
- [日志与监控](#日志与监控)
- [CLI 命令行](#cli-命令行)
- [Windows 已知问题](#windows-已知问题)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

核心依赖：`mcp>=1.25`、`duckdb`、`fastapi`、`uvicorn`、`sse-starlette`

### 2. 注册到 Claude Code

项目根目录 `.mcp.json` 已配置：

```json
{
  "mcpServers": {
    "doge-db": {
      "command": "scripts\\mcp_stdio.bat",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

启动脚本 `scripts/mcp_stdio.bat` 会自动检测项目级 venv，回退到系统 Python。

### 3. 验证

在 Claude Code 中调用：

```
mcp__doge-db__list_views
```

## 部署模式

| 模式 | 用途 | 启动方式 |
|------|------|----------|
| **stdio** | Claude Code 本地集成（默认） | `python doge_mcp.py` |
| **SSE** | HTTP 服务，供 Web 应用调用 | `python doge_mcp.py --transport sse --host 127.0.0.1 --port 8902` |

### 命令行参数

| 参数 | 可选值 | 默认 | 说明 |
|------|--------|------|------|
| `--transport` | `stdio`, `sse` | `stdio` | 传输协议 |
| `--host` | - | `127.0.0.1` | SSE 监听地址 |
| `--port` | - | `8902` | SSE 监听端口 |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` | 日志级别 |

## 工具清单

### query_stock

查询个股行情数据，含 OHLCV、均线、ATR、波动率等技术指标。

| 参数 | 类型 | 必填 | 默认 | 约束 | 说明 |
|------|------|------|------|------|------|
| `ticker` | string | 是 | - | 合法股票代码 | 股票代码，如 `601777`、`000858.SZ`、`AAPL` |
| `market` | string | 否 | `"cn"` | `"cn"` 或 `"us"` | 市场类型 |
| `days` | int | 否 | `20` | 1 ~ 500 | 返回天数 |

**CN 模式返回列：**

`date, open, high, low, close, volume, ret_pct, ma_5, ma_10, ma_20, ma_60, atr14, ma60_dev, vol_20d`

**US 模式返回列：**

`date, open, high, low, close, volume, amount`

**示例：**

```
mcp__doge-db__query_stock(ticker="601777", market="cn", days=3)
```

```
date        open   high   low    close  volume    ret_pct  ma_5   ma_10  ma_20  ma_60  atr14  ma60_dev  vol_20d
2026-05-07  11.00  11.40  10.92  11.32  58708796  2.63     11.20  10.92  10.53  10.43  0.40   8.54      1.75
2026-05-06  11.26  11.36  11.01  11.03  55991152  -1.78    11.16  10.80  10.47  10.42  0.38   5.86      1.76
2026-04-30  11.16  11.58  11.08  11.23  76064536  -0.18    11.10  10.70  10.42  10.42  0.37   7.81      1.68
```

---

### stock_overview

个股全景：名称、板块、最新价格与涨跌幅、用户笔记。

| 参数 | 类型 | 必填 | 默认 | 约束 | 说明 |
|------|------|------|------|------|------|
| `ticker` | string | 是 | - | 合法股票代码 | 股票代码 |
| `market` | string | 否 | `"cn"` | `"cn"` 或 `"us"` | 市场类型 |

数据来源（三合一）：

1. **名称与板块** — SQLite `stock_names` 表
2. **最近 10 日行情** — DuckDB `{cn|us}.stock_prices`，自动计算涨跌幅
3. **用户笔记** — SQLite `stock_notes` 表，显示总数和最近 5 条

**示例：**

```
mcp__doge-db__stock_overview(ticker="000858")
```

```
=== 000858.SZ (CN) ===
名称: 五 粮 液

最新数据: 2026-05-07
  收盘: 92.6
  涨跌幅: 0.37%

最近 10 天行情:
  2026-05-07 | O:92.43 H:93.85 L:92.43 C:92.6 V:53627788
  ...

笔记 (2 条):
  [2026-05-06] 茅台提价带动板块情绪，五粮液跟随上涨但力度偏弱，继续观察
```

---

### rsrs_ranking

RSRS 动量排名，返回趋势强度最高的 Top N 股票。

| 参数 | 类型 | 必填 | 默认 | 约束 | 说明 |
|------|------|------|------|------|------|
| `market` | string | 否 | `"cn"` | `"cn"` 或 `"us"` | 市场类型 |
| `top` | int | 否 | `20` | 1 ~ 100 | 返回数量 |

**RSRS 算法：** 对收盘价与时间序列做线性回归，`RSRS = R² × sign(slope)`，范围 -1.0 ~ +1.0。

**CN 返回列：**

`ticker, rsrs, avg_vol_20d, last_close, close_20d_ago, pct_change_20d, data_points, rank`

**US 返回列：**

`ticker, rsrs, avg_vol_20d, last_close, data_points, rank`

**示例：**

```
mcp__doge-db__rsrs_ranking(market="cn", top=3)
```

```
ticker     rsrs  avg_vol_20d  last_close  close_20d_ago  pct_change_20d  data_points  rank
603567.SH  0.95  19369926     7.09        6.79           4.42            117          1
600085.SH  0.95  5082476      27.59       27.57          0.07            117          2
001206.SZ  0.95  3401942      18.95       20.74          -8.63           117          3
```

---

### market_breadth

市场宽度：每日涨跌家数、上涨占比、平均涨跌幅。

| 参数 | 类型 | 必填 | 默认 | 约束 | 说明 |
|------|------|------|------|------|------|
| `market` | string | 否 | `"cn"` | `"cn"` 或 `"us"` | 市场类型 |
| `days` | int | 否 | `10` | 1 ~ 100 | 查询天数 |

**CN 返回列：**

`date, advancers, decliners, unchanged, active, avg_return_pct, std_return_pct, advance_ratio`

**US 返回列：** 同 CN 但无 `advance_ratio`。

**示例：**

```
mcp__doge-db__market_breadth(market="cn", days=3)
```

```
date        advancers  decliners  unchanged  active  avg_return_pct  std_return_pct  advance_ratio
2026-05-07  3246       1801       156        5203    1.13            3.13            62.39
2026-05-06  3645       1427       108        5180    1.43            3.26            70.37
2026-04-30  2658       2376       116        5150    0.36            3.31            51.61
```

---

### volume_anomalies

成交量异常检测（仅 A 股），发现放量异动。

| 参数 | 类型 | 必填 | 默认 | 约束 | 说明 |
|------|------|------|------|------|------|
| `min_ratio` | float | 否 | `3.0` | 1.0 ~ 1000.0 | 最低量比阈值 |
| `top` | int | 否 | `20` | 1 ~ 100 | 返回数量 |

**量比 = 当日成交量 / 前 20 日平均成交量。** `min_ratio=3.0` 表示当日成交量是 20 日均量的 3 倍以上。

**返回列：**

`ticker, date, volume, avg_vol, vol_ratio, ret_pct`

**示例：**

```
mcp__doge-db__volume_anomalies(min_ratio=5.0, top=5)
```

---

### list_views

列出所有可用的 DuckDB 分析视图及其行数和列名。无需参数。

**返回格式：** JSON 数组

```json
[
  {
    "view": "vw_daily_enriched_cn",
    "rows": 600690,
    "columns": "ticker, date, open, high, low, close, volume, amount, return_pct, ma_5, ma_10, ma_20, ma_60, atr_14, ma60_deviation, volatility_20d"
  }
]
```

## 数据库视图

7 个视图定义在 `data/views.sql`，由 DuckDB 在每次连接时从 SQLite 零拷贝计算。可通过 `list_views` 工具查看所有视图的行数和列名。

### vw_daily_enriched_cn

A 股日度宽表，最近 365 天。

| 列名 | 类型 | 说明 |
|------|------|------|
| `ticker` | TEXT | 股票代码 |
| `date` | TEXT | 交易日期 |
| `open, high, low, close` | REAL | OHLC |
| `volume` | INTEGER | 成交量 |
| `amount` | REAL | 成交额 |
| `return_pct` | REAL | 涨跌幅 (%) |
| `ma_5, ma_10, ma_20, ma_60` | REAL | N 日均线 |
| `atr_14` | REAL | 14 日平均真实波幅 |
| `ma60_deviation` | REAL | 距 60 日均线偏离度 (%) |
| `volatility_20d` | REAL | 20 日波动率 |

### vw_rsrs_ranking_cn

A 股 RSRS 动量排名，算法与 `momentum_scanner.py` 原始逻辑对齐：

1. 取最近 180 天数据，仅保留主板/创业板/科创板 (`00|30|60|68` 开头)
2. 过滤：`>= 61` 个交易日，`20 日均量 > 500,000`
3. 计算 **60 日涨幅** (最新 vs 60 交易日前)
4. 按 60 日涨幅取 **Top 200**
5. 对 Top 200 用最近 **18 天**收盘价做时间回归，RSRS = R² × sign(slope)
6. 最终按 RSRS 降序排列

| 列名 | 说明 |
|------|------|
| `ticker` | 股票代码 |
| `last_close` | 最新收盘价 |
| `close_60d_ago` | 60 天前收盘价 |
| `pct_change_60d` | **60 日涨跌幅 (%)** |
| `avg_vol_20d` | 20 日平均成交量 |
| `avg_amt_60d_wan` | 60 日平均成交额 (万) |
| `rsrs` | RSRS 值（6 位小数），范围 -1.0 ~ +1.0 |
| `rsrs_points` | 参与 RSRS 回归的数据点数 (18) |
| `rank` | DENSE_RANK 排名 |

**RSRS 解读：**

| 区间 | 含义 |
|------|------|
| > 0.8 | 极强上涨趋势 |
| 0.5 ~ 0.8 | 中等上涨趋势 |
| -0.5 ~ 0.5 | 震荡或无趋势 |
| -0.8 ~ -0.5 | 中等下跌趋势 |
| < -0.8 | 极强下跌趋势 |

### vw_market_breadth_cn

A 股市场宽度，最近 730 天。

| 列名 | 说明 |
|------|------|
| `date` | 交易日期 |
| `advancers` | 上涨家数 |
| `decliners` | 下跌家数 |
| `unchanged` | 平盘家数 |
| `active` | 活跃股票总数 |
| `avg_return_pct` | 全市场平均涨跌幅 |
| `std_return_pct` | 涨跌幅标准差 |
| `advance_ratio` | 上涨占比 (%) |

### vw_volume_anomalies_cn

A 股成交量异常（2025-01-01 起），量比 >= 2.0 的记录。

| 列名 | 说明 |
|------|------|
| `ticker` | 股票代码 |
| `date` | 交易日期 |
| `volume` | 当日成交量 |
| `avg_vol_20d` | 前 20 日平均成交量 |
| `vol_ratio` | 量比（当日/20日均量） |
| `intraday_return` | 日内涨跌幅 (%) |

### vw_cross_sectional_return_cn

A 股截面收益率分布，最近 365 天。

| 列名 | 说明 |
|------|------|
| `ticker, date` | 标识 |
| `return_pct` | 日涨跌幅 (%) |
| `volume, close` | 成交量与收盘价 |

### vw_market_breadth_us

美股市场宽度，最近 365 天。列同 CN 版本但无 `advance_ratio`。

### vw_rsrs_ranking_us

美股 RSRS 排名，算法与 CN 版本一致：
1. 最近 180 天数据，`>= 61` 个交易日
2. 过滤：`20 日均量 > 50,000`
3. 按 **60 日涨幅**取 Top 200
4. 对 Top 200 计算 18 日 RSRS

列名与 `vw_rsrs_ranking_cn` 相同，仅流动性门槛不同。

## 数据源

| 文件 | 类型 | 说明 |
|------|------|------|
| `data/market_data_cn.db` | SQLite | A 股 OHLCV（5,000+ 只股票） |
| `data/market_data_us.db` | SQLite | 美股 OHLCV |
| `data/research_insights.db` | SQLite | 研报、笔记、股票名称 |
| `data/views.sql` | SQL | 7 个 DuckDB 视图定义 |

**stock_prices 表结构：**

```sql
CREATE TABLE stock_prices (
    ticker TEXT,
    date TEXT,
    open REAL, high REAL, low REAL, close REAL,
    volume INTEGER, amount REAL,
    PRIMARY KEY (ticker, date)
);
```

**环境变量覆盖：**

| 变量 | 默认 | 说明 |
|------|------|------|
| `DOGE_DB_DIR` | `data/` | 数据库目录 |
| `DOGE_CN_DB` | `{DB_DIR}/market_data_cn.db` | A 股数据库路径 |
| `DOGE_US_DB` | `{DB_DIR}/market_data_us.db` | 美股数据库路径 |
| `DOGE_RESEARCH_DB` | `{DB_DIR}/research_insights.db` | 研究数据库路径 |
| `DEEPSEEK_API_KEY` | (无 — 生成 LLM 宏观报告必填) | Secret. 在 shell 环境中设置，切勿提交。`models_config.json` 只附带占位符 (`REPLACE_WITH_DEEPSEEK_API_KEY`)；`src/macro/config.py` 在缺失时会抛出 `RuntimeError`。 |

> **Operator action — key verification (S002-013):** a forensic audit of the
> repository confirmed that no real DeepSeek key was ever committed to git
> history (`models_config.json` was gitignored from the initial commit; no
> `sk-...` key appears in 82 commits, 4 refs, reflog, or dangling objects).
> The code remediation (placeholder swap + env-var read) ships here; the
> **operator must export `DEEPSEEK_API_KEY`** in the local environment and verify
> that `python -m macro.cli` produces a macro report. No key rotation or history
> rewriting is required.

### DeepSeek API Key

The MCP server itself does not call the LLM, but the macro strategy engine
(Module #4, `src/macro/strategist.py`) reads `DEEPSEEK_API_KEY` from the
environment. As of S002-013 this is the PRIMARY key source; export it before
launching any macro report run:

**Windows (cmd):**
```cmd
set DEEPSEEK_API_KEY=sk-your-real-key-here
```

**Windows (PowerShell):**
```powershell
$env:DEEPSEEK_API_KEY='sk-your-real-key-here'
```

**macOS / Linux (bash):**
```bash
export DEEPSEEK_API_KEY=sk-your-real-key-here
```

To switch models at runtime (GUI model-switching), also set `DEEPSEEK_MODEL`
(e.g. `deepseek-chat` or `deepseek-reasoner`).

## SSE 模式 HTTP 接口

启动 SSE 模式后，额外提供两个 HTTP 端点：

### GET /health

健康检查。

```bash
curl http://127.0.0.1:8902/health
# {"status": "ok"}
```

### GET /metrics

Prometheus 格式的工具调用指标。

```bash
curl http://127.0.0.1:8902/metrics
```

返回的指标类型：
- `mcp_requests_total{tool="..."}` — 工具调用次数
- `mcp_request_duration_seconds_sum{tool="..."}` — 调用耗时总和
- `mcp_request_duration_seconds_count{tool="..."}` — 调用次数

## 配置

### 启动脚本

| 脚本 | 用途 |
|------|------|
| `scripts/mcp_stdio.bat` / `.sh` | stdio 模式（Claude Code 用） |
| `scripts/start_mcp_sse.bat` / `.sh` | SSE 模式（Web 用） |

脚本自动检测项目 venv（`venv/Scripts/python.exe`），回退到系统 Python。SSE 模式可通过 `MCP_HOST`/`MCP_PORT` 环境变量覆盖地址。

### Claude Code Skills

4 个 CLI skill 位于 `.claude/skills/`，作为 MCP 工具的 Bash 替代路径：

| Skill | 命令 | 说明 |
|-------|------|------|
| `stock` | `doge stock <ticker>` | 行情查询 |
| `rsrs` | `doge rsrs` | 动量排名 |
| `breadth` | `doge breadth` | 市场宽度 |
| `anomaly` | `doge anomaly` | 量比异动 |

## 日志与监控

| 文件 | 位置 | 说明 |
|------|------|------|
| `logs/mcp_server.log` | 自动创建 | RotatingFileHandler，10MB x 5 备份 |
| `mcp_crash.log` | 项目根目录 | 未捕获异常记录 |

**日志格式：**

```
2026-05-10 21:23:38,873 [INFO] [405b8d30] doge-mcp: TOOL CALL: query_stock ok duration=0.451s result_len=447
```

每条工具调用带唯一 correlation_id（UUID 前 8 位），便于追踪。

## CLI 命令行

`doge` 提供查询子命令，功能与 MCP 工具等价，使用 `tabulate` 格式化输出。`src/cli.py` 仍作为兼容 shim 保留，但不再是推荐入口：

```bash
doge stock 601777 --market cn --days 5
doge rsrs --market cn --top 10
doge breadth --market cn --days 7
doge anomaly --min-ratio 5.0 --top 10
```

## Windows 已知问题

### stdout 双重 TextIOWrapper 冲突

**现象：** `OSError: [Errno 22] Invalid argument`，崩溃日志指向 `mcp/server/stdio.py:81` 的 `stdout.flush()`。

**原因：** MCP SDK 内部创建 `TextIOWrapper(sys.stdout.buffer)` 与 Python 原始 `sys.stdout` 共享同一个 `BufferedWriter`。Windows 上两个 TextIOWrapper 同时 flush 导致冲突。

**修复：** `doge_mcp.py` / `src/doge/interfaces/mcp/server.py` 的 stdio 模式已包含修复——在 SDK 接管前将 `sys.stdout.buffer` 保存到独立变量，`sys.stdout` 替换为 `io.StringIO()`，然后传自定义 stdout 给 `stdio_server(stdout=cl_stdout)`。

### ticker 格式

CN 股票代码自动补后缀：`6xx/68x` -> `.SH`，`0xx/3xx` -> `.SZ`，`4xx/8xx` -> `.BJ`。输入时可带可不带后缀。仅允许 `[A-Za-z0-9.\-]` 字符。
