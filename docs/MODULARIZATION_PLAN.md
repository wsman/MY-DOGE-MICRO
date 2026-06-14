# MY-DOGE 彻底模块化改造方案

## 现状诊断

### 核心问题

| 反模式 | 数量 | 文件示例 | 危害 |
|---|---|---|---|
| `sys.path.insert` | legacy sites remain | `ai_analysis/*.py`, `micro/*.py`, API/CLI legacy modules | 项目不是真正的 Python 包；根 MCP monolith 已在 Wave 4 删除 |
| `_PROJECT_ROOT` 重复计算 | 10+ | `api/routers/*.py`, `interface/*.py` | 硬编码路径分散，维护困难 |
| 路由直接 `import sqlite3` | 8+ | `macro.py`, `data.py`, `analysis.py` | API 层耦合数据库实现 |
| `connect_duckdb()` 直接调用 | 6+ | `cli.py`, `market_overview.py` | 无连接抽象，难以测试 |
| `ai_analysis/__init__.py` 职责过多 | 1 | 200+ 行 | 包含路径、连接、工具函数 |
| 循环依赖 | 2+ | `micro → ai_analysis → micro` | 架构脆弱 |

### 循环依赖图

```
cli.py ──→ ai_analysis (connect_duckdb)
api/routers/scan.py ──→ micro/tdx_downloader ──→ ai_analysis (run_views_sql)
micro/market_scanner.py ──→ ai_analysis (connect_duckdb)
macro/strategist.py ←── micro/industry_analyzer.py
```

## 目标架构：Clean Architecture + Ports & Adapters

```
src/doge/                    ← 包根
├── __init__.py
│
├── config/                  ← 集中配置（单一真相源）
│   ├── __init__.py
│   └── settings.py          # 所有路径、常量、环境变量
│
├── core/                    ← 核心业务（纯 Python，无外部依赖）
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   └── models.py        # Stock, OHLCV, Ticker
│   ├── ports/               # 抽象接口（ABC）
│   │   ├── __init__.py
│   │   ├── repository.py    # IStockRepository, IReportRepository
│   │   ├── data_source.py   # IMarketDataSource
│   │   └── cache.py         # ITickerNameCache
│   └── services/            # 业务服务
│       ├── __init__.py
│       ├── stock_service.py      # query_stock, stock_overview
│       ├── ranking_service.py    # rsrs_ranking
│       ├── breadth_service.py    # market_breadth
│       └── anomaly_service.py    # volume_anomalies
│
├── infrastructure/          ← 基础设施（适配器实现）
│   ├── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── duckdb.py        # DuckDB 连接池（替代 ai_analysis.connect_duckdb）
│   │   ├── sqlite.py        # SQLite 连接管理
│   │   └── repositories.py  # 仓库实现（注入到服务）
│   ├── data_source/
│   │   ├── __init__.py
│   │   ├── tdx.py           # TDX 客户端（替代 tdx_downloader）
│   │   └── yfinance.py
│   └── cache/
│       ├── __init__.py
│       └── ticker_cache.py  # 股票名称缓存（替代 _ticker_names_cache）
│
├── application/             ← 应用层（用例编排）
│   ├── __init__.py
│   └── use_cases/
│       ├── __init__.py
│       ├── sync_market_data.py
│       └── generate_report.py
│
└── interfaces/              ← 接口适配（用户界面）
    ├── __init__.py
    ├── api/                 # FastAPI（只依赖 services，不直接访问 DB）
    │   ├── __init__.py
    │   ├── deps.py          # 依赖注入容器
    │   └── routers/         # 复用现有路由，注入服务
    ├── cli/                 # CLI
    │   ├── __init__.py
    │   └── main.py
    ├── mcp/                 # MCP Server
    │   ├── __init__.py
    │   ├── server.py
    │   └── tools/           # 工具实现（通过服务层）
    └── gui/                 # GUI
        └── __init__.py
```

## 依赖规则（强制执行）

```
interfaces/ ──→ application/ ──→ core/services/ ──→ core/ports/ 〈────┐
     │                  │                              │              │
     │                  └──────────────────────────────┘              │
     │                                                                │
     └──────────────────────────────────────────────────────────────┘
                            infrastructure/
```

- **interfaces/** 只依赖 **core/services** 和 **application**
- **core/services** 只依赖 **core/ports**（抽象接口）
- **infrastructure/** 实现 **core/ports** 中的接口
- **不允许**底层依赖上层
- **不允许**跨越端口直接操作基础设施

## 迁移批次

### 批次 1：基础设施（pyproject.toml + config + 消除 sys.path）
- 创建 `pyproject.toml` — `pip install -e .`
- 创建 `src/doge/config/settings.py` — 集中所有路径、常量
- 消除所有 `sys.path.insert`（通过包安装解决）
- 消除所有 `_PROJECT_ROOT` 计算

### 批次 2：数据访问抽象（DuckDB + SQLite Repository）
- 创建 `src/doge/core/ports/repository.py` — IStockRepository 等 ABC
- 创建 `src/doge/infrastructure/database/duckdb.py`
- 创建 `src/doge/infrastructure/database/sqlite.py`
- 创建 `src/doge/infrastructure/database/repositories.py`
- 迁移 `ai_analysis/__init__.py` 中的连接逻辑

### 批次 3：数据源抽象（TDX 适配器）
- 创建 `src/doge/core/ports/data_source.py` — IMarketDataSource
- 创建 `src/doge/infrastructure/data_source/tdx.py`
- 迁移 `tdx_downloader.py` 核心逻辑

### 批次 4：业务服务层
- 创建 `src/doge/core/services/*.py`
- 将 MCP tool 逻辑提取为服务
- 将 CLI 查询逻辑提取为服务
- 服务通过构造函数接收 Repository 端口

### 批次 5：接口层重构
- MCP 已完成：`doge_mcp.py` → `src/doge/interfaces/mcp/server.py`（Wave 4 删除旧 monolith）
- `src/cli.py` → `src/doge/interfaces/cli/main.py`
- `src/api/routers/*.py` — 注入服务替代直接 DB 操作
- 添加 `deps.py` 依赖注入容器

### 批次 6：清理与测试
- 删除旧兼容代码
- 运行所有测试
- 验证 MCP 工具、CLI、API 正常工作
