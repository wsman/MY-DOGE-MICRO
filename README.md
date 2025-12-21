# MY-DOGE QUANT SYSTEM

**MY-DOGE QUANT SYSTEM** 是一个本地优先（Local-First）的量化投资战略指挥平台。它集成了通达信（TDX）本地数据清洗、宏观战略定调（Macro Beta）、微观动量选股（Micro Alpha）以及基于 LLM 的深度行业分析功能，旨在为个人投资者提供机构级的决策辅助。

## 目录

- [项目概览](#项目概览)
- [核心功能](#核心功能)
- [系统架构](#系统架构)
  - [架构图](#架构图)
  - [数据流](#数据流)
- [组件详解](#组件详解)
  - [数据清洗管道](#数据清洗管道)
  - [宏观策略引擎](#宏观策略引擎)
  - [AI行业分析](#ai行业分析)
  - [知识库系统](#知识库系统)
- [配置详解](#配置详解)
  - [models_config.json 结构](#models_configjson-结构)
  - [资产配置选项](#资产配置选项)
  - [API设置与代理](#api设置与代理)
- [快速开始](#快速开始)
  - [环境准备](#环境准备)
  - [启动系统](#启动系统)
  - [使用步骤](#使用步骤)
- [开发指南](#开发指南)
  - [项目结构](#项目结构)
  - [关键代码文件](#关键代码文件)
  - [模块扩展指南](#模块扩展指南)
  - [数据库Schema演进](#数据库schema演进)
  - [自定义过滤规则](#自定义过滤规则)
- [常见问题](#常见问题)
- [许可证](#许可证)

## 项目概览

MY-DOGE QUANT SYSTEM 采用三层架构，将数据清洗、策略生成和用户交互分离，确保系统的高内聚低耦合。所有数据本地存储，不依赖云服务，保护用户隐私并降低延迟。

本系统设计目标：
- **数据主权**：所有数据本地存储，无云端依赖。
- **模块化**：三层架构，各层职责清晰，易于扩展。
- **智能化**：集成 DeepSeek 大模型，提供宏观策略和行业分析。
- **易用性**：图形化界面，一键操作，适合非编程用户。

## 核心功能

* **📊 双轨制数据中心** – 支持 A 股与美股的全量历史数据导入、清洗与本地存储，完全摆脱对昂贵数据终端的依赖。
* **🌍 宏观战略定调** – 一键生成宏观对冲策略报告，自动计算波动率窗口与资产相关性，由 AI 判定当前市场水位。
* **🧠 行业景气度扫描** – 结合宏观背景与微观强势股清单，利用大模型推理产业链共振逻辑，生成结构化研报。
* **🛡️ 智能风控** – 内置 ETF 黑名单与反向拆股熔断机制，自动过滤市场噪音。
* **💾 研报智库** – 自动归档所有分析报告至本地数据库，支持历史回溯与知识沉淀。

## 系统架构

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                   交互层 (Interface Layer)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  市场扫描  │ │  A股档案  │ │ 美股档案  │ │  研报智库  │      │
│  │  Scanner  │ │ CN Data  │ │ US Data  │ │ Insights │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 行业扫描 (Analysis)                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   微观层 (Micro Layer)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │TDX数据解析│ │市场扫描与 │ │动量策略   │ │数据库管理  │      │
│  │TDXLoader │ │ Market   │ │Momentum  │ │Database  │      │
│  │          │ │ Scanner  │ │ Scanner  │ │          │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   宏观层 (Macro Layer)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │配置管理   │ │数据加载器 │ │策略生成器  │                    │
│  │ Config   │ │DataLoader│ │Strategist│                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

1. **数据摄入**：通达信 `.day` 文件 → TDXReader（解析） → 过滤清洗（白名单） → SQLite 数据库
2. **宏观分析**：yfinance 获取全球资产数据 → 计算波动率/相关性 → 调用 DeepSeek API → 生成报告并归档
3. **行业分析**：读取宏观报告 + 动量选股结果 → 调用 DeepSeek API 进行产业链推理 → 生成行业研报并归档
4. **知识沉淀**：所有报告自动保存至 `research_insights.db`，支持查询和回溯。

各层之间通过文件系统（数据库文件、报告文件）和信号槽（GUI 通信）进行交互，保证模块间低耦合。

## 组件详解

### 数据清洗管道

- **功能**：从通达信 `vipdoc` 目录读取 A 股/美股的日线数据（`.day` 文件），经过清洗后存入 SQLite 数据库。
- **关键实现**：
  - `TDXReader` (`src/micro/tdx_loader.py`) 负责解析二进制文件，根据市场类型使用不同的解包格式。
  - `MarketScanner` (`src/micro/market_scanner.py`) 批量遍历文件，应用过滤规则，并通过回调函数更新 GUI 进度条。
- **数据清洗规则**：
  - **A 股**：只保留代码以 `00` (深市主板)、`30` (创业板)、`60` (沪市主板)、`68` (科创板) 开头的 6 位数字代码，剔除指数、基金、债券等。
  - **美股**：只保留纯大写字母组成的代码（如 `AAPL`、`NVDA`），剔除港股（含 `HK`）及数字代码。
- **进度管理**：扫描过程中每处理 50 只股票更新一次进度，避免 GUI 卡顿。

### 宏观策略引擎

- **功能**：通过 `yfinance` 获取 QQ (纳斯达克 100 ETF)、GLD (黄金 ETF)、BTC-USD (比特币) 和 000300.SS (沪深300) 的历史数据，计算波动率窗口和资产相关性，并调用 DeepSeek 生成宏观风险信号（Risk-On / Risk-Off）及详细报告。
- **配置驱动**：所有资产配置、API 设置、参数均通过 `models_config.json` 管理，支持动态加载和运行时覆盖。
- **指标计算**：
  - 波动率（年化）
  - 中期趋势（整个周期）
  - 短期动量（最近5日）
  - 风险信号（Risk-On / Risk-Off）
- **报告归档**：生成的宏观报告自动保存至 `macro_report/` 目录，同时调用 `save_macro_report` 将内容写入 `research_insights.db` 的 `macro_reports` 表，便于后续查询。

### AI行业分析

- **功能**：结合最新宏观报告与动量选股结果（CSV 文件），利用 DeepSeek 进行产业链推理，挖掘强势股背后的行业逻辑，生成结构化行业研报。
- **报告归档**：研报保存至 `research_report/` 目录，并通过 `save_research_report` 写入 `research_insights.db` 的 `research_reports` 表。

### 知识库系统

- **数据库文件**：
  - `data/market_data_cn.db`：A 股日线数据
  - `data/market_data_us.db`：美股日线数据
  - `data/research_insights.db`：宏观报告与行业研报归档
- **表结构**：
  - **`stock_prices`** – 存储个股日线行情
    ```sql
    (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER, amount REAL, PRIMARY KEY (ticker, date))
    ```
  - **`macro_reports`** – 存储宏观策略报告（V2 结构）
    ```sql
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
     date TEXT, timestamp TEXT, tags TEXT, analyst TEXT,
     risk_signal TEXT, volatility TEXT, content TEXT)
    ```
  - **`research_reports`** – 存储行业深度研报（V2 结构）
    ```sql
    (id INTEGER PRIMARY KEY AUTOINCREMENT,
     date TEXT, timestamp TEXT, tags TEXT, analyst TEXT,
     title TEXT, content TEXT)
    ```
- **自动迁移**：`_ensure_columns` 函数会在插入数据前检查表结构，自动添加缺失的列（如 `tags`、`analyst` 等），保障版本升级时数据平滑过渡。
- **系统初始化**：`initialize_system_dbs()` 在启动 GUI 前调用，确保所有数据库文件和表存在，实现“冷启动”即用。

## 配置详解

### models_config.json 结构

配置文件位于项目根目录，模板为 `models_config.template.json`。复制并重命名为 `models_config.json` 后编辑。

```json
{
    "profiles": [
        {
            "name": "🚀 DeepSeek Chat (Standard)",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "api_key": "YOUR_API_KEY_HERE"
        },
        {
            "name": "🧠 DeepSeek Reasoner (R1 - Pro)",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-reasoner",
            "api_key": "YOUR_API_KEY_HERE"
        },
        {
            "name": "🏠 LM Studio (Local)",
            "base_url": "http://localhost:1234/v1",
            "model": "local-model",
            "api_key": "lm-studio"
        }
    ],
    "default_profile": "🚀 DeepSeek Chat (Standard)",
    "macro_settings": {
        "lookback_days": 120,
        "volatility_window": 20
    },
    "assets": {
        "tech": {
            "symbol": "QQQ",
            "name": "科技股(纳指)"
        },
        "safe": {
            "symbol": "GLD",
            "name": "避险黄金"
        },
        "crypto": {
            "symbol": "BTC-USD",
            "name": "数字货币"
        },
        "target": {
            "symbol": "000300.SS",
            "name": "A股核心(沪深300)"
        }
    },
    "proxy_settings": {
        "enabled": false,
        "url": "http://127.0.0.1:7890"
    }
}
```

### 资产配置选项

- `tech`: 科技股代理，默认 QQQ（纳斯达克100 ETF）
- `safe`: 避险资产代理，默认 GLD（黄金 ETF）
- `crypto`: 加密货币代理，默认 BTC-USD（比特币）
- `target`: 目标市场代理，默认 000300.SS（沪深300指数）

每个资产包含 `symbol`（代码）和 `name`（显示名称），可在配置中修改。

### API设置与代理

- **API Key**：从 DeepSeek 平台获取，填入对应 profile 的 `api_key` 字段。
- **模型选择**：支持 `deepseek-chat`（标准）和 `deepseek-reasoner`（推理）等。
- **代理配置**：若需代理，设置 `proxy_settings.enabled` 为 `true` 并填写 `url`。
- **本地模型**：支持 LM Studio 等本地 API 服务，修改 `base_url` 和 `model` 即可。

## 快速开始

### 环境准备

- **Python 3.8+**
- 安装依赖：
  ```bash
  pip install -r requirements.txt
  ```
- **配置 API Key**：
  复制模板文件并填写 DeepSeek API 信息：
  ```bash
  cp models_config.template.json models_config.json
  ```
  编辑 `models_config.json`，填入您的 API Key 和模型偏好（推荐使用 `deepseek-reasoner` 或 `deepseek-chat`）。
- **通达信数据准备**：
  确保已安装通达信金融终端，并下载完整的日线数据。
  默认数据目录为 `vipdoc`，通常位于 `D:/New_TDX/vipdoc` 或类似路径。如果只提供根目录（如 `D:/New_TDX`），系统会自动检测并添加 `vipdoc` 子目录。

### 启动系统

```bash
python src/interface/dashboard.py
```

### 使用步骤

1. **市场扫描**
   - 在“市场扫描”标签页输入通达信路径（如 `D:/New_TDX`），点击“启动扫描（A股）”或“启动扫描（美股）”。
   - 扫描完成后，数据库文件会自动生成在 `data/` 目录下，相应档案标签页将解锁并显示数据。

2. **宏观分析**
   - 在“市场扫描”标签页点击“启动 宏观分析”按钮，系统将拉取全球资产数据并生成宏观报告。
   - 报告会弹出预览并自动归档。

3. **行业深度分析**
   - 切换到“行业扫描”标签页，选择已生成的宏观报告（Markdown 文件）和动量选股结果（CSV 文件），点击“执行”按钮。
   - DeepSeek 将生成行业景气度分析报告，弹出预览并保存至 `research_report/`。

4. **数据库管理**
   - 在“A股档案”、“美股档案”、“研报智库”标签页中，您可以浏览、搜索、编辑底层数据，支持 SQL 查询和表格操作。

## 开发指南

### 项目结构

```
MY-DOGE-MICRO/
├── data/               # 数据库文件（自动生成）
├── macro_report/       # 宏观策略报告输出目录
├── micro_report/       # 动量选股结果输出目录
├── research_report/    # AI 行业研报输出目录
├── src/
│   ├── interface/      # 图形用户界面
│   │   ├── dashboard.py        # 主控制台
│   │   ├── scanner_gui.py      # 扫描界面组件
│   │   ├── db_editor.py        # 数据库编辑组件
│   │   └── analysis_gui.py     # 行业分析界面
│   ├── macro/          # 宏观层
│   │   ├── strategist.py       # 宏观信号生成
│   │   ├── config.py           # 配置文件读取
│   │   ├── data_loader.py      # 全球数据加载
│   │   └── utils.py            # 工具函数
│   └── micro/          # 微观层（数据清洗、动量、数据库）
│       ├── tdx_loader.py       # 通达信数据解析
│       ├── market_scanner.py   # 市场扫描与过滤
│       ├── database.py         # 数据库操作（含自动迁移）
│       ├── momentum_scanner.py # 动量策略
│       └── industry_analyzer.py # 行业分析器
├── models_config.template.json # API 配置模板
├── proxy_config_guide.md      # 代理配置指南
├── requirements.txt    # 依赖清单
├── README.md           # 项目文档
└── LICENSE             # 许可证
```

### 关键代码文件

- **`src/micro/tdx_loader.py`** – 通达信 `.day` 文件解析器，支持 A 股与美股不同格式。
- **`src/micro/market_scanner.py`** – 扫描入口，调用 `TDXReader` 并应用过滤规则，批量写入数据库。
- **`src/micro/database.py`** – 数据库初始化、表结构定义、自动迁移和归档函数。
- **`src/macro/config.py`** – JSON 驱动的配置加载器，支持运行时覆盖。
- **`src/macro/data_loader.py`** – 通过 yfinance 获取全球资产数据，计算波动率、相关性等指标。
- **`src/macro/strategist.py`** – 宏观信号计算与 DeepSeek API 调用，生成结构化报告。
- **`src/interface/dashboard.py`** – 主窗口，集成各子组件，处理信号通信。

### 模块扩展指南

1. **添加新的数据源**：
   - 继承或修改 `TDXReader` 类，支持新的文件格式。
   - 在 `MarketScanner` 中添加相应的扫描方法。

2. **增加新的策略指标**：
   - 在 `src/macro/data_loader.py` 的 `calculate_metrics` 方法中添加计算逻辑。
   - 在 `src/macro/strategist.py` 的 `generate_strategy_report` 方法中调整 prompt，使 DeepSeek 能使用新指标。

3. **更换大模型提供商**：
   - 修改 `MacroConfig` 中的 `base_url` 和 `model` 配置。
   - 调整 `DeepSeekStrategist` 中的 API 调用方式（目前使用 OpenAI 兼容格式）。

### 数据库Schema演进

系统内置自动迁移机制（`_ensure_columns` 函数）。当表结构需要升级时，只需在插入数据前调用该函数，它会检查并添加缺失的列。

例如，若要为 `macro_reports` 表新增一列 `confidence`，只需在插入数据前确保该列存在：

```python
_ensure_columns(cursor, "macro_reports", [("confidence", "REAL")])
```

### 自定义过滤规则

若要修改 A 股或美股的过滤规则，请编辑 `src/micro/market_scanner.py`：

- **A 股**：修改 `scan_cn_market` 函数中的 `if code.startswith(...)` 条件。
- **美股**：修改 `scan_us_market` 函数中的正则表达式 `re.match(r'^[A-Z]+$', raw_code)`。

## 常见问题

**Q: 扫描时找不到通达信目录怎么办？**  
A: 系统会自动尝试在输入的路径后添加 `vipdoc`。请确保输入的是正确的通达信根目录（例如 `D:/New_TDX`），且该目录下存在 `vipdoc` 子目录。

**Q: 运行提示缺少 `openai` 模块，但已安装 `openai`？**  
A: 本项目使用 `openai` 包与 DeepSeek 通信，请确保已安装且版本 >= 1.0.0。若问题依旧，尝试 `pip install --upgrade openai`。

**Q: 如何自定义过滤规则，例如加入创业板或科创板以外的股票？**  
A: 修改 `src/micro/market_scanner.py` 中 `scan_cn_market` 函数的代码，调整 `if code.startswith(...)` 条件即可。

**Q: 数据库表结构升级后如何保留旧数据？**  
A: `_ensure_columns` 函数会在插入数据前自动添加缺失列，旧数据中新增列将为 `NULL`。若需要更复杂的迁移，可手动执行 SQL 脚本。

**Q: 如何更换为其他大模型 API？**  
A: 修改 `models_config.json` 中的 `base_url` 和 `model`，并确保 API 兼容 OpenAI 格式。如果需要不同的调用方式，需修改 `src/macro/strategist.py` 中的 `DeepSeekStrategist` 类。

**Q: 代理设置不生效？**  
A: 请检查 `proxy_settings.enabled` 是否为 `true`，并且 `url` 格式正确（如 `http://127.0.0.1:7890`）。同时确保网络环境支持代理。

## 许可证

本项目基于 Apache License 2.0 开源。允许商业使用、修改和分发，但必须保留原始版权声明。详情请参阅 LICENSE 文件。

---

*MY-DOGE QUANT SYSTEM – 让量化投研触手可及。*
