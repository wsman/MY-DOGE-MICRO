# MY-DOGE QUANT SYSTEM

**MY-DOGE QUANT SYSTEM** 是一个本地优先（Local-First）的量化投资战略指挥平台。它集成了通达信（TDX）本地数据清洗、宏观战略定调（Macro Beta）、微观动量选股（Micro Alpha）以及基于 LLM 的深度行业分析功能，旨在为个人投资者提供机构级的决策辅助。

## 目录

- [项目概览](#项目概览)
- [核心功能](#核心功能)
- [系统架构](#系统架构)
- [组件详解](#组件详解)
  - [数据清洗管道 (Data Pipeline)](#数据清洗管道-data-pipeline)
  - [宏观策略引擎 (Macro Engine)](#宏观策略引擎-macro-engine)
  - [AI 行业分析 (Industry Analysis)](#ai-行业分析-industry-analysis)
  - [知识库系统 (Knowledge Base)](#知识库系统-knowledge-base)
- [API 调用与模型集成](#api-调用与模型集成)
- [配置详解](#配置详解)
- [快速开始](#快速开始)
- [开发指南](#开发指南)

## 项目概览

MY-DOGE QUANT SYSTEM 采用**三层架构**，将数据清洗、策略生成和用户交互分离。所有数据本地存储，不依赖云服务，保护用户隐私并降低延迟。

本系统设计目标：
- **数据主权**：所有数据本地存储 (SQLite)，无云端依赖。
- **消除幻觉**：在 AI 推理过程中引入实时联网校准 (Real-time Calibration)，确保行业归类准确。
- **量化风控**：结合 LLM 的定性分析与 RSRS/VolSkew 等硬核定量指标。
- **易用性**：PyQt6 图形化界面，一键操作。

## 核心功能

*   **📊 双轨制数据中心** – 支持 A 股与美股的全量历史数据导入、清洗与本地存储，完全摆脱对昂贵数据终端的依赖。
*   **🌍 宏观战略定调** – 一键生成宏观对冲策略报告。
    *   **量化仪表盘**：集成 **RSRS (阻力支撑相对强度)** 判断趋势强度，**Vol Skew (波动率偏度)** 预警变盘风险。
    *   **AI 决策**：由 DeepSeek 判定当前市场水位 (Risk-On / Risk-Off)。
*   **🧠 行业景气度扫描** – 结合宏观背景与微观强势股清单，利用大模型推理产业链共振逻辑。
    *   **防幻觉机制**：自动并发调用 `yfinance` 校验股票名称与所属板块，修正 AI 的认知偏差。
    *   **语义化归档**：自动提取研报核心结论作为标题进行归档。
*   **📈 动量选股** – 基于修正的动量模型筛选强势股。
*   **💾 研报智库** – 自动归档所有分析报告至本地数据库，支持历史回溯与知识沉淀。

## 系统架构

### 三层架构

```
┌─────────────────────────────────────────────────────────────┐
│                   交互层 (Interface Layer)                   │
│  [Dashboard] 主控台集成                                      │
│  ├── 🚀 市场扫描 (Scanner)                                   │
│  ├── 🇨🇳/🇺🇸 档案局 (Data Editor)                              │
│  ├── 🧠 研报智库 (Insights)                                  │
│  └── 🔎 行业扫描 (Analysis)                                  │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   微观层 (Micro Layer)                      │
│  [TDXLoader] 通达信解析  →  [MarketScanner] 清洗过滤         │
│  [Momentum] 动量计算     →  [IndustryAnalyzer] 行业分析      │
│  (特性: 实时联网校准股票元数据)                               │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   宏观层 (Macro Layer)                      │
│  [DataLoader] 全球资产数据 (yfinance)                        │
│  [Strategist] 策略生成 (DeepSeek API)                        │
│  (特性: RSRS趋势 + VolSkew风控 + 结构化Prompt)               │
└─────────────────────────────────────────────────────────────┘
```

### 数据流转 (Data Flow)

1.  **数据摄入**: 通达信 `.day` 文件 → 清洗过滤 → `market_data_*.db`
2.  **宏观定调**: 全球资产数据 → 计算量化指标 (RSRS, VolSkew) → **DeepSeek 推理** → 生成 `Macro Report`
3.  **行业分析**: 
    *   输入: `Macro Report` (宏观背景) + `Momentum CSV` (强势股)
    *   **校准**: 并发联网获取 Top 50 股票的真实业务信息
    *   推理: **DeepSeek** 归纳产业链共振逻辑
    *   输出: `Industry Report` (存入 `research_insights.db`)

## 组件详解

### 数据清洗管道 (Data Pipeline)

-   **TDXReader**: 高性能解析通达信二进制数据 (`src/micro/tdx_loader.py`)。
-   **MarketScanner**: 
    -   **A股过滤**: 保留 `00`, `30`, `60`, `68` 开头代码，剔除指数/基金。
    -   **美股过滤**: 仅保留纯字母代码，剔除粉单/OTC。

### 宏观策略引擎 (Macro Engine)

-   **位置**: `src/macro/strategist.py`
-   **量化仪表盘 (Quantitative Dashboard)**:
    -   **RSRS (Slope*R2)**: 衡量趋势的强度与质量。正值越大，趋势越强。
    -   **Vol Skew (5d/20d)**: 短期与中期波动率的比值。`< 0.8` 暗示变盘在即，`> 1.5` 暗示恐慌释放。
-   **Prompt Engineering**:
    -   采用 **System Prompt** 强制要求数据引用 ("根据数据 [120天趋势 +5.2%]...")。
    -   严禁混淆短期波动与长期趋势。

### AI 行业分析 (Industry Analysis)

-   **位置**: `src/micro/industry_analyzer.py`
-   **工作流程**:
    1.  **加载上下文**: 自动读取最新的宏观报告摘要 (Risk Signal)。
    2.  **加载微观数据**: 读取动量选股生成的 CSV 文件。
    3.  **联网校准 (关键特性)**: 使用 `ThreadPoolExecutor` 并发请求 `yfinance`，获取 Top 50 股票的准确名称和行业分类，注入到 Prompt 中。这有效解决了 LLM 对 A 股代码/名称对应的幻觉问题。
    4.  **深度推理**: DeepSeek 识别细分赛道集群，生成产业链图谱。
    5.  **自动归档**: 正则提取报告中的 `TITLE:` 字段，以语义化标题存入数据库。

### 知识库系统 (Knowledge Base)

-   **数据库**: `data/research_insights.db`
-   **表结构**:
    -   `macro_reports`: 存储宏观策略，包含风险信号和波动率数据。
    -   `research_reports`: 存储行业研报，包含语义化标题和完整分析。
-   **冷启动**: `initialize_system_dbs()` 确保系统首次运行时自动创建所有必要的表结构。

## API 调用与模型集成

### DeepSeek 集成

系统深度集成 DeepSeek API，支持多种模型配置：

-   **DeepSeek Chat (v3)**: 适用于行业分析、文本生成，速度快，逻辑通顺。
-   **DeepSeek Reasoner (R1)**: 适用于宏观复杂逻辑推理，擅长处理多变量博弈。

### 配置管理 (`models_config.json`)

```json
{
    "profiles": [
        {
            "name": "🚀 DeepSeek Chat",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "api_key": "sk-..."
        }
    ],
    "macro_settings": {
        "lookback_days": 120,  // 中期趋势窗口
        "volatility_window": 20 // 波动率窗口
    },
    "assets": {
        "tech": { "symbol": "QQQ", "name": "科技股" },
        "safe": { "symbol": "GLD", "name": "黄金" },
        "crypto": { "symbol": "BTC-USD", "name": "比特币" }
    }
}
```

## 快速开始

### 1. 环境准备

```bash
pip install -r requirements.txt
```

### 2. 配置 API

复制模板并填入 API Key：
```bash
cp models_config.template.json models_config.json
# 编辑 models_config.json 填入你的 DeepSeek API Key
```

### 3. 启动系统

```bash
python src/interface/dashboard.py
```

### 4. 操作流程

1.  **数据准备**: 在 **"市场扫描"** 页签，设置通达信路径 (如 `D:/New_TDX`)，执行 A 股/美股扫描。
2.  **宏观定调**: 点击 **"启动 宏观分析"**，系统将拉取全球数据并生成策略报告。
3.  **行业挖掘**: 切换到 **"行业扫描"** 页签，选择宏观报告和动量 CSV，点击 **"执行"**。系统将自动联网校准数据并生成深度研报。
4.  **复盘**: 在 **"研报智库"** 中查看历史分析记录。

## 开发指南

-   **目录结构**:
    -   `src/interface`: PyQt6 界面逻辑
    -   `src/macro`: 宏观策略、API 交互、全球数据加载
    -   `src/micro`: 通达信解析、动量计算、行业分析、数据库管理
-   **扩展**:
    -   若需添加新指标，请修改 `src/macro/data_loader.py` 中的 `calculate_advanced_metrics`。
    -   若需调整 AI 提示词，请修改 `src/macro/strategist.py` 或 `src/micro/industry_analyzer.py`。

## 许可证

Apache License 2.0
