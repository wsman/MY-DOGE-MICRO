# MY-DOGE QUANT SYSTEM

**MY-DOGE QUANT SYSTEM** 是一个本地优先（Local-First）的量化投资战略指挥平台。它集成了通达信（TDX）本地数据清洗、宏观战略定调（Macro Beta）、微观动量选股（Micro Alpha）以及基于 LLM 的深度行业分析功能，旨在为个人投资者提供机构级的决策辅助。



## 核心架构 (Architecture)

本项目采用三层架构设计，确保数据主权与策略的灵活性：

1.  **交互层 (Interface Layer)**: 
    - 基于 `PyQt6` 构建的现代化指挥控制台 (`dashboard.py`)。
    - 支持多任务并行：数据扫描、数据库管理、AI 深度推理。
2.  **微观层 (Micro Layer)**:
    - **Market Scanner**: 极速解析通达信二进制数据 (`.day`)，构建本地 A 股/美股 SQLite 数据库。
    - **Momentum Engine**: 独立的动量策略脚本，用于捕捉市场中的强势标的。
3.  **宏观层 (Macro Layer)**:
    - **Global Strategist**: 集成 DeepSeek API (V3/R1)，结合纳指 (QQQ)、黄金 (GLD)、BTC 和 沪深300 的数据，输出 Risk-On/Risk-Off 宏观信号。

## 主要功能 (Features)

* **📊 双轨制数据中心**: 支持 A 股与美股的全量历史数据导入、清洗与本地存储，完全摆脱对昂贵数据终端的依赖。
* **🌍 宏观战略定调**: 一键生成宏观对冲策略报告，自动计算波动率窗口与资产相关性，由 AI 判定当前市场水位。
* **🧠 行业景气度扫描**: 结合宏观背景与微观强势股清单，利用大模型推理产业链共振逻辑，生成结构化研报。
* **🛡️ 智能风控**: 内置 ETF 黑名单与反向拆股熔断机制，自动过滤市场噪音。
* **💾 研报智库**: 自动归档所有分析报告至本地数据库，支持历史回溯与知识沉淀。

## 系统依赖 (Requirements)

* **Python**: 3.8+
* **GUI Framework**: PyQt6
* **Data Analysis**: pandas, numpy, yfinance
* **Database**: sqlite3 (内置)
* **LLM API**: openai (用于调用 DeepSeek 协议接口)

详细依赖请见 `requirements.txt`。

## 快速开始 (Quick Start)

### 1. 安装
```bash
git clone https://github.com/wsman/MY-DOGE-MICRO.git
cd MY-DOGE-MICRO
pip install -r requirements.txt
```
### 2. 配置
复制模板文件并配置您的 API Key（推荐使用 DeepSeek）：

```bash
cp models_config.template.json models_config.json
# 编辑 models_config.json 填入您的 API Key 和模型偏好
```

### 3. 数据源准备
本项目依赖通达信 (TDX) 的本地数据文件。

请确保您已安装通达信金融终端，并下载了完整的日线数据。

默认选择路径为根目录，如 D:/New_TDX

### 4. 启动指挥官系统
```bash
python src/interface/dashboard.py
```

## 使用指南 (User Guide)

### 市场扫描 (Tab 1):

输入通达信 VIPDOC 路径，点击“启动扫描”。系统将自动建立 market_data_cn.db 和 market_data_us.db。

### 宏观分析:

在扫描界面点击“启动 宏观分析”，系统将拉取全球资产数据并生成 Markdown 战略报告。

### 行业深度分析:

进入“AI 分析”界面，选择宏观报告与动量 CSV 文件，点击执行。DeepSeek 将为您生成行业景气度全景图谱。

### 数据库管理:

在“档案局”与“研报智库”标签页中，您可以直接查看、搜索和编辑底层数据。

## License

本项目基于 Apache License 2.0 开源。允许商业使用、修改和分发，但必须保留原始版权声明。详情请参阅 LICENSE 文件。

