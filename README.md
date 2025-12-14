# MY-DOGE QUANT SYSTEM

**MY-DOGE QUANT SYSTEM** 是一个本地优先（Local-First）的量化投资战略指挥平台。它集成了通达信（TDX）本地数据清洗、宏观战略定调（Macro Beta）、微观动量选股（Micro Alpha）以及基于 LLM 的深度行业分析功能，旨在为个人投资者提供机构级的决策辅助。

## 目录
- [项目概览](#项目概览)
- [主要功能](#主要功能)
- [系统架构](#系统架构)
- [组件详解](#组件详解)
  - [市场扫描模块](#市场扫描模块)
  - [数据库模块](#数据库模块)
  - [宏观策略模块](#宏观策略模块)
  - [AI行业分析模块](#ai行业分析模块)
  - [图形界面](#图形界面)
- [快速开始](#快速开始)
  - [环境准备](#环境准备)
  - [启动系统](#启动系统)
  - [使用步骤](#使用步骤)
- [开发指南](#开发指南)
  - [项目结构](#项目结构)
  - [关键代码文件](#关键代码文件)
- [常见问题](#常见问题)
- [许可证](#许可证)

## 项目概览

MY-DOGE QUANT SYSTEM 采用三层架构，将数据清洗、策略生成和用户交互分离，确保系统的高内聚低耦合。所有数据本地存储，不依赖云服务，保护用户隐私并降低延迟。

## 主要功能

* **📊 双轨制数据中心** – 支持 A 股与美股的全量历史数据导入、清洗与本地存储，完全摆脱对昂贵数据终端的依赖。
* **🌍 宏观战略定调** – 一键生成宏观对冲策略报告，自动计算波动率窗口与资产相关性，由 AI 判定当前市场水位。
* **🧠 行业景气度扫描** – 结合宏观背景与微观强势股清单，利用大模型推理产业链共振逻辑，生成结构化研报。
* **🛡️ 智能风控** – 内置 ETF 黑名单与反向拆股熔断机制，自动过滤市场噪音。
* **💾 研报智库** – 自动归档所有分析报告至本地数据库，支持历史回溯与知识沉淀。

## 系统架构

本项目采用三层架构设计，确保数据主权与策略的灵活性：

- **交互层 (Interface Layer)**  
  基于 `PyQt6` 构建的现代化指挥控制台 (`dashboard.py`)，提供多任务并行界面：数据扫描、数据库管理、AI 深度推理。

- **微观层 (Micro Layer)**  
  - **Market Scanner**：极速解析通达信二进制数据 (`.day`)，构建本地 A 股/美股 SQLite 数据库。  
  - **Momentum Engine**：独立的动量策略脚本，用于捕捉市场中的强势标的。

- **宏观层 (Macro Layer)**  
  - **Global Strategist**：集成 DeepSeek API (V3/R1)，结合纳指 (QQQ)、黄金 (GLD)、BTC 和 沪深300 的数据，输出 Risk-On/Risk-Off 宏观信号。

各层之间通过文件系统（数据库文件、报告文件）和信号槽（GUI 通信）进行交互，保证模块间低耦合。

## 组件详解

### 市场扫描模块

- **功能**  
  从通达信 `vipdoc` 目录读取 A 股/美股的日线数据（`.day` 文件），经过清洗后存入 SQLite 数据库。

- **关键实现**  
  - `TDXReader` (`src/micro/tdx_loader.py`) 负责解析二进制文件，根据市场类型使用不同的解包格式。
  - `MarketScanner` (`src/micro/market_scanner.py`) 批量遍历文件，应用过滤规则，并通过回调函数更新 GUI 进度条。

- **数据清洗规则**  
  - **A 股**：只保留代码以 `00` (深市主板)、`30` (创业板)、`60` (沪市主板)、`68` (科创板) 开头的 6 位数字代码，剔除指数、基金、债券等。
  - **美股**：只保留纯大写字母组成的代码（如 `AAPL`、`NVDA`），剔除港股（含 `HK`）及数字代码。

- **进度管理**  
  扫描过程中每处理 50 只股票更新一次进度，避免 GUI 卡顿。

### 数据库模块

- **数据库文件**  
  - `data/market_data_cn.db`：A 股日线数据  
  - `data/market_data_us.db`：美股日线数据  
  - `data/research_insights.db`：宏观报告与行业研报归档

- **表结构**  
  **`stock_prices`** – 存储个股日线行情  
  ```sql
  (ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER, amount REAL, PRIMARY KEY (ticker, date))
  ```

  **`macro_reports`** – 存储宏观策略报告（V2 结构）  
  ```sql
  (id INTEGER PRIMARY KEY AUTOINCREMENT,
   date TEXT, timestamp TEXT, tags TEXT, analyst TEXT,
   risk_signal TEXT, volatility TEXT, content TEXT)
  ```

  **`research_reports`** – 存储行业深度研报（V2 结构）  
  ```sql
  (id INTEGER PRIMARY KEY AUTOINCREMENT,
   date TEXT, timestamp TEXT, tags TEXT, analyst TEXT,
   title TEXT, content TEXT)
  ```

- **自动迁移**  
  `_ensure_columns` 函数会在插入数据前检查表结构，自动添加缺失的列（如 `tags`、`analyst` 等），保障版本升级时数据平滑过渡。

- **系统初始化**  
  `initialize_system_dbs()` 在启动 GUI 前调用，确保所有数据库文件和表存在，实现“冷启动”即用。

### 宏观策略模块

- **功能**  
  通过 `yfinance` 获取 QQ (纳斯达克 100 ETF)、GLD (黄金 ETF)、BTC-USD (比特币) 和 000300.SS (沪深300) 的历史数据，计算波动率窗口和资产相关性，并调用 DeepSeek 生成宏观风险信号（Risk-On / Risk-Off）及详细报告。

- **报告归档**  
  生成的宏观报告自动保存至 `macro_report/` 目录，同时调用 `save_macro_report` 将内容写入 `research_insights.db` 的 `macro_reports` 表，便于后续查询。

### AI行业分析模块

- **功能**  
  结合最新宏观报告与动量选股结果（CSV 文件），利用 DeepSeek 进行产业链推理，挖掘强势股背后的行业逻辑，生成结构化行业研报。

- **报告归档**  
  研报保存至 `research_report/` 目录，并通过 `save_research_report` 写入 `research_insights.db` 的 `research_reports` 表。

### 图形界面

- **控制台** (`src/interface/dashboard.py`)  
  采用标签页布局，包含：
  - 🚀 市场扫描 (Scanner) – 输入通达信路径，启动 A 股/美股扫描。
  - 🇨🇳 A股档案 (CN Data) – 浏览和编辑 A 股数据库。
  - 🇺🇸 美股档案 (US Data) – 浏览和编辑美股数据库。
  - 🧠 研报智库 (Insights) – 查看历史宏观报告和行业研报。
  - 🔎 行业扫描 (Analysis) – 执行 AI 行业分析。

- **信号槽通信**  
  扫描开始/结束时通过信号锁定或解锁对应标签页，并自动刷新数据视图。

## 快速开始

### 环境准备

- **Python 3.8+**
- 安装依赖：
  ```bash
  pip install -r requirements.txt
  ```
- **配置 API Key**  
  复制模板文件并填写 DeepSeek API 信息：
  ```bash
  cp models_config.template.json models_config.json
  ```
  编辑 `models_config.json`，填入您的 API Key 和模型偏好（推荐使用 `deepseek-reasoner` 或 `deepseek-chat`）。

- **通达信数据准备**  
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
│   │   └── ...
│   └── micro/          # 微观层（数据清洗、动量、数据库）
│       ├── tdx_loader.py       # 通达信数据解析
│       ├── market_scanner.py   # 市场扫描与过滤
│       ├── database.py         # 数据库操作
│       ├── momentum_scanner.py # 动量策略
│       └── ...
├── models_config.template.json # API 配置模板
├── requirements.txt    # 依赖清单
└── README.md           # 项目文档
```

### 关键代码文件

- **`src/micro/tdx_loader.py`** – 通达信 `.day` 文件解析器，支持 A 股与美股不同格式。
- **`src/micro/market_scanner.py`** – 扫描入口，调用 `TDXReader` 并应用过滤规则，批量写入数据库。
- **`src/micro/database.py`** – 数据库初始化、表结构定义、自动迁移和归档函数。
- **`src/macro/strategist.py`** – 宏观信号计算与 DeepSeek 调用。
- **`src/interface/dashboard.py`** – 主窗口，集成各子组件，处理信号通信。

## 常见问题

**Q: 扫描时找不到通达信目录怎么办？**  
A: 系统会自动尝试在输入的路径后添加 `vipdoc`。请确保输入的是正确的通达信根目录（例如 `D:/New_TDX`），且该目录下存在 `vipdoc` 子目录。

**Q: 运行提示缺少 `openai` 模块，但已安装 `openai`？**  
A: 本项目使用 `openai` 包与 DeepSeek 通信，请确保已安装且版本 >= 1.0.0。若问题依旧，尝试 `pip install --upgrade openai`。

**Q: 如何自定义过滤规则，例如加入创业板或科创板以外的股票？**  
A: 修改 `src/micro/market_scanner.py` 中 `scan_cn_market` 函数的代码，调整 `if code.startswith(...)` 条件即可。

**Q: 数据库表结构升级后如何保留旧数据？**  
A: `_ensure_columns` 函数会在插入数据前自动添加缺失列，旧数据中新增列将为 `NULL`。若需要更复杂的迁移，可手动执行 SQL 脚本。

## 许可证

本项目基于 Apache License 2.0 开源。允许商业使用、修改和分发，但必须保留原始版权声明。详情请参阅 LICENSE 文件。

---

*MY-DOGE QUANT SYSTEM – 让量化投研触手可及。*
