# MY-DOGE CLI 命令参考

MY-DOGE 提供两个独立的命令行入口，覆盖「只读行情查询」与「LLM 宏观报告生成」两类本地操作。本文档为操作者的命令参考，所有命令均基于本地 DuckDB / SQLite 数据与（可选）DeepSeek API。

> **适用范围**：本文档仅描述产品 CLI。Claude Code / MCP 客户端通过 `doge_mcp.py` 调用工具的方式，参见 [docs/MCP_SERVER.md](MCP_SERVER.md)。

## 目录

- [概述](#概述)
- [安装与调用](#安装与调用)
- [查询 CLI：`python src/cli.py`](#查询-clipython-srcclipy)
  - [doge stock](#doge-stock)
  - [doge rsrs](#doge-rsrs)
  - [doge breadth](#doge-breadth)
  - [doge anomaly](#doge-anomaly)
- [输出格式](#输出格式)
- [宏观 CLI：`python -m macro.cli`](#宏观-clipython--macrocli)
- [退出码](#退出码)
- [环境变量](#环境变量)
- [MCP 服务器命令行参数](#mcp-服务器命令行参数)

---

## 概述

| CLI | 入口 | 数据源 | 用途 |
|-----|------|--------|------|
| **查询 CLI** | `python src/cli.py` | DuckDB 只读视图 | A 股 / 美股行情、RSRS 动量、市场宽度、成交量异动的本地只读查询 |
| **Demo CLI** | `python src/cli.py demo` | DuckDB 只读视图 | 5 分钟无配置演示，无需 `DEEPSEEK_API_KEY` |
| **宏观 CLI** | `python -m macro.cli` | DeepSeek API + yfinance 宏观数据 | 调用 DeepSeek 生成宏观对冲策略报告 |

查询 CLI 的 `argparse` `prog` 名为 `doge`（`src/cli.py:114-117`），但 **当前并未注册为已安装的 console script**（详见下节）；宏观 CLI 无 `prog` 别名。

两个 CLI 均不在 ADR-0001 目标架构的「端口/服务」层内，是 Wave-3 清理迁移之前的存量入口。

## 安装与调用

### 依赖安装

```bash
pip install -e .            # 通过 pyproject.toml 安装（推荐）
# 或
pip install -r requirements.txt
```

`pyproject.toml` 已锁定核心依赖（`duckdb==1.4.4`、`tabulate==0.10.0`、`openai==1.62.0` 等，见 `pyproject.toml:10-26`）。可选 extras：`[gui]=PyQt6`、`[tdx]=opentdx`、`[cn]=akshare`（`pyproject.toml:28-31`）。

### 无 console_scripts — 直接 `python` 调用

> **重要**：`pyproject.toml` **未声明任何 `[project.scripts]` console_scripts 入口**。因此系统中 **不存在** `doge` 可执行命令。所有调用必须通过 `python src/cli.py ...` 与 `python -m macro.cli ...` 完成。

```bash
# 查询 CLI
python src/cli.py stock 301599.SZ --market cn --days 20

# 5 分钟演示（无需 DeepSeek key）
python src/cli.py demo

# 宏观 CLI（在仓库根目录运行）
python -m macro.cli --verbose
```

### 引导垫片已清理

`src/cli.py` 不再包含 `sys.path.insert` 垫片（Wave-3 Batch-1 已清理；见
ADR-0001）。它依赖 `pip install -e .` 激活的可编辑安装，使 `doge`、`micro`、
`macro` 等包作为顶层包可用。

`src/macro/cli.py` 仍保留其历史垫片（另一入口），属于后续清理范围。

---

## 查询 CLI：`python src/cli.py`

`src/cli.py` 通过 `argparse` + `add_subparsers`（`src/cli.py:212`）暴露 5 个子命令，分发在 `src/cli.py:246-251`。所有子命令均通过 `doge.core.services.composition` 中的工厂注入只读仓库适配器，**不写入数据库**。

子命令概览：

| 子命令 | 摘要 | 关键参数 | 源码 |
|--------|------|----------|------|
| [`stock`](#doge-stock) | 查询个股行情与指标 | `ticker`、`--market`、`--days` | `src/cli.py:215-218` |
| [`rsrs`](#doge-rsrs) | RSRS 动量排名 | `--market`、`--top` | `src/cli.py:221-223` |
| [`breadth`](#doge-breadth) | 市场宽度（涨跌家数） | `--market`、`--days` | `src/cli.py:226-228` |
| [`anomaly`](#doge-anomaly) | 成交量异动检测 | `--min-ratio`、`--top` | `src/cli.py:231-233` |
| [`demo`](#doge-demo) | 5 分钟无配置演示 | `--market`、`--top` | `src/cli.py:236-238` |

不带子命令运行 `python src/cli.py` 会打印帮助并返回（`src/cli.py:241-243`）。

### doge stock

查询个股 OHLCV 与技术指标。

| 参数 | 类型 | 必填 | 默认 | 约束 | 说明 | 源码 |
|------|------|------|------|------|------|------|
| `ticker` | string | 是 | — | 合法股票代码 | 如 `301599.SZ`、`AAPL`；经 `normalize_ticker` 规范化 | `src/cli.py:216` |
| `--market` | string | 否 | `cn` | `choices=["cn","us"]` | 市场类型 | `src/cli.py:217` |
| `--days` | int | 否 | `20` | 正整数 | 返回最近 N 个交易日 | `src/cli.py:218` |

**Synopsis**

```bash
python src/cli.py stock <ticker> [--market cn|us] [--days N]
```

**示例**

```bash
# A 股，默认 cn / 20 日
python src/cli.py stock 301599.SZ

# 美股，60 日
python src/cli.py stock AAPL --market us --days 60
```

**返回列（CN，`vw_daily_enriched_cn`，`src/cli.py:25-36`）**：`date, open, high, low, close, volume, ret_pct, ma_5, ma_10, ma_20, ma_60, atr14, ma60_dev, vol_20d`
**返回列（US，`us.stock_prices`，`src/cli.py:38-44`）**：`date, open, high, low, close, volume, amount`

数据为空时打印 `no data for <ticker>` 并返回（`src/cli.py:88-90`）。

### doge rsrs

RSRS 动量排名（最强趋势股票排行）。

| 参数 | 类型 | 必填 | 默认 | 约束 | 说明 | 源码 |
|------|------|------|------|------|------|------|
| `--market` | string | 否 | `cn` | `choices=["cn","us"]` | 选择 `vw_rsrs_ranking_cn` / `vw_rsrs_ranking_us` | `src/cli.py:222` |
| `--top` | int | 否 | `20` | 正整数 | 返回前 N 名 | `src/cli.py:223` |

**Synopsis**

```bash
python src/cli.py rsrs [--market cn|us] [--top N]
```

**示例**

```bash
# 默认 cn / 前 20
python src/cli.py rsrs

# 美股前 10
python src/cli.py rsrs --market us --top 10
```

**返回列**：`rank, ticker, rsrs, avg_vol_20d, last_close`，若视图存在 `pct_change_60d` 则附加（`src/cli.py:159-161`）。数据为空时打印 `no data`（`src/cli.py:103-105`）。

### doge breadth

市场宽度（每日涨跌家数、上涨占比、平均涨跌幅）。

| 参数 | 类型 | 必填 | 默认 | 约束 | 说明 | 源码 |
|------|------|------|------|------|------|------|
| `--market` | string | 否 | `cn` | `choices=["cn","us"]` | 选择 `vw_market_breadth_cn` / `vw_market_breadth_us` | `src/cli.py:227` |
| `--days` | int | 否 | `10` | 正整数 | 返回最近 N 个交易日 | `src/cli.py:228` |

**Synopsis**

```bash
python src/cli.py breadth [--market cn|us] [--days N]
```

**示例**

```bash
python src/cli.py breadth --market cn --days 30
```

数据为空时打印 `no data`（`src/cli.py:120-122`）。

### doge anomaly

成交量异动检测（量比排名，发现放量异动）。

| 参数 | 类型 | 必填 | 默认 | 约束 | 说明 | 源码 |
|------|------|------|------|------|------|------|
| `--min-ratio` | float | 否 | `3.0` | 正浮点 | 最小量比阈值（`vol_ratio >= ?`） | `src/cli.py:232` |
| `--top` | int | 否 | `20` | 正整数 | 返回前 N 条 | `src/cli.py:233` |

> 注：当前仅查询 CN 视图 `vw_volume_anomalies_cn`，**不接受 `--market` 参数**。

**Synopsis**

```bash
python src/cli.py anomaly [--min-ratio F] [--top N]
```

**示例**

```bash
python src/cli.py anomaly --min-ratio 5.0 --top 50
```

**返回列**：`ticker, date, volume, avg_vol, vol_ratio, ret_pct`。无结果时打印 `no anomalies found`（`src/cli.py:132-134`）。

### doge demo

5 分钟无配置演示，使用 `data/` 下的 bundled 样本数据依次展示 RSRS 排名、市场宽度、成交量异动和个股查询。无需 `DEEPSEEK_API_KEY`。

| 参数 | 类型 | 必填 | 默认 | 约束 | 说明 | 源码 |
|------|------|------|------|------|------|------|
| `--market` | string | 否 | `cn` | `choices=["cn","us"]` | 选择 CN / US 样本数据 | `src/cli.py:237` |
| `--top` | int | 否 | `5` | 正整数 | 每个查询返回前 N 条 | `src/cli.py:238` |

**Synopsis**

```bash
python src/cli.py demo [--market cn|us] [--top N]
```

**示例**

```bash
# 默认 cn / 前 5
python src/cli.py demo

# 美股样本
python src/cli.py demo --market us --top 10
```

任一查询返回数据即视为成功（退出码 0）。所有查询都为空时打印帮助信息并以 `EXIT_NO_DATA`（1）退出（`src/cli.py:195-200`）。

---

## 输出格式

所有子命令使用 `tabulate`（`tablefmt="simple"`、`showindex=False`）输出对齐的纯文本表格。各命令的浮点格式化由 `floatfmt` 元组控制：

| 子命令 | `floatfmt` 顺序 |
|--------|-----------------|
| `stock` (CN) | `.0f, .2f, .2f, .2f, .2f, .0f` |
| `rsrs` | `.0f, .6f, .0f, .2f, .2f, .2f` |
| `breadth` | `.0f, .0f, .0f, .2f, .2f` |
| `anomaly` | `.0f, .2f, .2f` |
| `demo` | 复用上述四个子命令的格式 |

输出始终面向终端，**无 JSON / CSV 输出开关**；脚本化解析建议改用 MCP 工具（见 [docs/MCP_SERVER.md](MCP_SERVER.md)）或 FastAPI 端点（见 `docs/API.md`）。

---

## 宏观 CLI：`python -m macro.cli`

`src/macro/cli.py` 是独立的宏观策略 CLI，调用 DeepSeek 生成宏观对冲策略报告。它**不读取 DuckDB**，而是通过 `GlobalMacroLoader`（yfinance）拉取宏观数据，再交由 `DeepSeekStrategist` 生成报告（`src/macro/cli.py:61-78`）。

| 参数 | 类型 | 默认 | 说明 | 源码 |
|------|------|------|------|------|
| `--verbose` | flag | — | 显示详细输出（实际行为见下方说明） | `src/macro/cli.py:31-35` |
| `--config-file` | string | — | 指定配置文件路径 — **已接受但未实现（no-op）** | `src/macro/cli.py:37-40` |

**Synopsis**

```bash
python -m macro.cli [--verbose] [--config-file PATH]
```

**示例**

```bash
python -m macro.cli --verbose
```

### 关于 `--verbose` 与 `--config-file` 的当前行为

- **`--verbose`**：参数被解析并保存到 `args.verbose`（`src/macro/cli.py:42`），但日志级别在 `src/macro/cli.py:47` 被 **无条件** 设为 `logging.DEBUG`，因此无论是否传入 `--verbose`，输出都相同（始终为详细模式）。该 flag 在当前实现中为 **无实际效果**。
- **`--config-file PATH`**：参数被接受，但 help 文本明确标注「暂未实现」（`src/macro/cli.py:39`），CLI 主体（`src/macro/cli.py:55-87`）**从不读取** `args.config_file`。该参数为 **no-op**，配置始终来自 `MacroConfig` → `models_config.json` + 环境变量（见 [环境变量](#环境变量)）。

> **技术债标记**：两个 flag 的「接受但不生效」语义应在后续清理中统一——要么实现，要么移除。本表据实记录当前行为。

宏观 CLI 的失败路径见 [退出码](#退出码)。

---

## 退出码

### 查询 CLI（`src/cli.py`）— 当前状态（含已知缺口）

| 场景 | 退出码 | 源码 |
|------|--------|------|
| 成功（有数据） | `0`（隐式，函数返回 `None`） | `src/cli.py:146-152` |
| 无数据（打印 `no data` / `no anomalies found`） | `1`（`EXIT_NO_DATA`） | `src/cli.py:41`（常量）、`:89`/`:102`/`:120`/`:133`（`sys.exit(EXIT_NO_DATA)`） |
| 无效参数（如非法 `--market`） | `2`（argparse 标准错误退出） | `argparse` 内置 |
| 未带子命令 | `0`（打印 help 后返回） | `src/cli.py:142-144` |

> 「无数据」与「成功」由 `EXIT_NO_DATA = 1`（`src/cli.py:41`）区分 —— 脚本化调用 `doge stock` 可直接凭退出码判断「该股票无数据」。此前的隐式 `0` 缺口已在 ADR-0001 清理迁移期间修复（`src/cli.py:81` docstring 记录了 `instead of the prior implicit 0`）。

### 宏观 CLI（`src/macro/cli.py`）

| 场景 | 退出码 | 源码 |
|------|--------|------|
| 成功（生成报告） | `0`（隐式） | `src/macro/cli.py:55-78` |
| 市场数据获取失败（`market_data is None`） | `1`（显式 `sys.exit(1)`） | `src/macro/cli.py:80-82` |
| 任意异常（含缺失 `DEEPSEEK_API_KEY` 触发的 `RuntimeError`） | `1`（显式 `sys.exit(1)`） | `src/macro/cli.py:84-87` |

宏观 CLI 的「空数据」与「异常」均映射到退出码 `1`，**不区分**二者。脚本若需区分原因，应解析 stderr / stdout 文本（`❌ 无法获取市场数据...` vs `❌ 运行失败: ...`）。

---

## 环境变量

### 宏观 CLI 所需

| 变量 | 必填 | 默认 | 说明 | 源码 |
|------|------|------|------|------|
| `DEEPSEEK_API_KEY` | **是** | — | DeepSeek API 密钥，**主来源**。`models_config.json` 仅内置占位符 `REPLACE_WITH_DEEPSEEK_API_KEY`；若环境变量未设且 JSON 仍为占位符，`MacroConfig.__post_init__` 抛 `RuntimeError`（Wave-1 S002-013 已交付） | `src/macro/config.py:185-200` |
| `DEEPSEEK_MODEL` | 否 | `deepseek-chat`（来自 `models_config.json` 默认 profile） | 运行时模型覆盖（GUI 用其切换模型） | `src/macro/config.py:189-191` |

> 占位符校验已交付：`src/macro/config.py:193-200` 在 `self.api_key` 为空或等于 `REPLACE_WITH_DEEPSEEK_API_KEY` 时抛 `RuntimeError`，**不会** 让占位符静默流入 `OpenAI(...)`。解析顺序：① `DEEPSEEK_API_KEY` 环境变量优先 → ② 否则用 JSON 中的值，但占位符会被拒绝。

### 查询 CLI 所需（DuckDB 路径）

查询 CLI 通过 `ai_analysis.connect_duckdb` 间接读取下列路径变量（定义在 `src/doge/config/settings.py` 的 `DBConfig`，`settings.py:52-67`）：

| 变量 | 默认 | 说明 | 源码 |
|------|------|------|------|
| `DOGE_DB_DIR` | `<root>/data` | 数据目录根 | `settings.py:55` |
| `DOGE_CN_DB` | `<dir>/market_data_cn.db` | A 股 SQLite | `settings.py:63` |
| `DOGE_US_DB` | `<dir>/market_data_us.db` | 美股 SQLite | `settings.py:64` |
| `DOGE_RESEARCH_DB` | `<dir>/research_insights.db` | 研究 SQLite | `settings.py:65` |
| `DOGE_DUCKDB_PATH` | `<dir>/market.duckdb` | DuckDB 分析库（视图 attach 到此） | `settings.py:66` |

> `DOGE_RETENTION_DAYS`（默认 `730`，`settings.py:112`）影响**写入**路径的保留期，不影响查询 CLI 的只读行为；详见 `docs/operations-runbook.md`（待撰写）。

完整环境变量总览另见 [docs/MCP_SERVER.md](MCP_SERVER.md) 的「配置」章节。

---

## MCP 服务器命令行参数

`doge_mcp.py` 严格意义上**不是**产品查询 CLI（它服务于 MCP 客户端），但操作者常以命令行启动它。为便于交叉查阅，此处列出其 `argparse` 参数（由 `src/doge/interfaces/mcp/server.py` 提供）：

| 参数 | 可选值 | 默认 | 说明 |
|------|--------|------|------|
| `--transport` | `stdio`, `sse` | `stdio` | 传输协议 |
| `--host` | — | `127.0.0.1` | SSE 监听地址 |
| `--port` | int | `8902` | SSE 监听端口 |
| `--log-level` | `DEBUG`/`INFO`/`WARNING`/`ERROR` | `INFO` | 日志级别 |

启动脚本与详细用法参见 [docs/GETTING_STARTED.md](GETTING_STARTED.md)（待撰写）与 [docs/MCP_SERVER.md](MCP_SERVER.md) 的「部署模式」「命令行参数」章节。

---

## 相关文档

- [docs/MCP_SERVER.md](MCP_SERVER.md) — MCP 工具（`query_stock` / `rsrs_ranking` / `market_breadth` / `volume_anomalies`）与服务启动
- [docs/GETTING_STARTED.md](GETTING_STARTED.md) — 操作者快速上手（含 MCP / FastAPI / Web 启动，待撰写）
- `docs/architecture/adr-0001-brownfield-clean-architecture.md` — `sys.path.insert` 禁止模式与清理迁移目标
- `docs/architecture/adr-0005-llm-client-strategy.md` — DeepSeek 客户端与密钥处理策略
