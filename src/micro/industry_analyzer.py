import os
import pandas as pd
import glob
from datetime import datetime
import yfinance as yf
import concurrent.futures # 用于并发加速获取信息
import json
import threading

# S002-009 / TR-011: package-qualified sibling imports resolve via the editable
# install (no sys.path shim). Paths come from get_settings().project_root.
from doge.config import get_settings

# --- 导入 ---
try:
    from macro.config import MacroConfig
    from macro.strategist import DeepSeekStrategist
except ImportError as e:
    print(f"[ERR] 模块导入失败: {e}")

# 导入数据库保存函数
try:
    from micro.database import save_research_report
except ImportError:
    print("[WARN] Warning: Could not import database module")
    save_research_report = lambda *args, **kwargs: None

class IndustryAnalyzer:
    def __init__(self, logger_callback=None, proxy='http://127.0.0.1:7890'):
        self.config = MacroConfig()
        self.strategist = DeepSeekStrategist(self.config)
        # S002-009: project root sourced from centralized Settings, not a local
        # dirname walk (ADR-0001 forbidden pattern ``_PROJECT_ROOT``).
        self.project_root = str(get_settings().project_root)
        self.logger_callback = logger_callback
        self.cache_file = os.path.join(self.project_root, 'data', 'meta_cache.json')
        self.cache_lock = threading.RLock()
        self.metadata_cache = self._load_cache()
        # 用于记录本次分析中新获取的股票代码
        self.newly_fetched_tickers = set()
        
        # 设置yfinance代理（通过环境变量）
        self.proxy = proxy
        os.environ['HTTP_PROXY'] = proxy
        os.environ['HTTPS_PROXY'] = proxy

    def load_latest_file(self, pattern):
        """加载最新的文件"""
        files = glob.glob(pattern)
        if not files:
            return None
        return max(files, key=os.path.getctime)

    def log(self, message):
        """日志输出：同时打印到控制台和回调函数"""
        print(message)
        if self.logger_callback:
            self.logger_callback(message)

    def _format_stock_line(self, row, name, sector):
        """统一格式化股票信息行"""
        # [NEW] 增加 RSRS 数据的展示
        # 如果 csv 中没有 rsrs_z 列，默认为 0.0
        rsrs_val = row.get('rsrs_z', 0.0)
        
        # 增加一个视觉标记：RSRS > 0.8 为强趋势 ([HOT])
        trend_mark = "[HOT]" if rsrs_val > 0.8 else ""
        
        return (
            f"- {row['ticker']} [{name}] ({sector}) "
            f"| 涨幅: +{row['change_percent']}% "
            f"| RSRS: {rsrs_val} {trend_mark}"
        )

    def _process_csv(self, file_path, market_type):
        """处理 CSV 文件并注入元数据（供外部调用）"""
        df = pd.read_csv(file_path)
        # 取前 50 名，避免 Token 溢出，且头部效应最明显
        top_50 = df.head(50) 
        
        self.log(f"[SEARCH] 正在联网校准 {market_type} 前 50 名股票的业务信息...")
        stock_list_str = []
        
        # 并发获取，避免卡顿
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_ticker = {executor.submit(self.get_stock_metadata, row['ticker']): row for _, row in top_50.iterrows()}
            
            for future in concurrent.futures.as_completed(future_to_ticker):
                row = future_to_ticker[future]
                name, sector = future.result()
                
                # [MODIFIED] 调用统一的格式化函数
                line = self._format_stock_line(row, name, sector)
                stock_list_str.append(line)
        
        return "\n".join(stock_list_str)

    def load_macro_context(self):
        """读取最新的宏观报告摘要"""
        # 更新路径以包含 'macro_report'
        report_dir = os.path.join(self.project_root, 'macro_report')
        latest_report = self.load_latest_file(os.path.join(report_dir, "*.md"))
        
        if not latest_report:
            return "N/A", "N/A", "No macro report found in macro_report/"
            
        with open(latest_report, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 简单解析 Risk Signal 和 Volatility (假设格式固定)
        risk = "Risk-Off" if "Risk-Off" in content else "Risk-On"
        vol = "Unknown" # 可以加正则提取 17.xx%
        
        # 截取前 1000 字作为摘要
        summary = content[:1000] 
        return risk, vol, summary

    def _load_cache(self):
        """加载本地缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        """保存缓存到文件（原子写入，避免数据损坏）"""
        with self.cache_lock:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            # 使用临时文件进行原子写入
            import tempfile
            temp_dir = os.path.dirname(self.cache_file)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                             dir=temp_dir, delete=False) as f:
                json.dump(self.metadata_cache, f, ensure_ascii=False)
                temp_path = f.name
            # 原子替换
            import shutil
            shutil.move(temp_path, self.cache_file)
            
    def _save_snapshot(self):
        """保存本次分析中新获取的公司数据快照"""
        if not self.newly_fetched_tickers:
            self.log("[INFO] 本次分析没有获取到新的公司数据")
            return
        
        # 提取本次获取的数据
        snapshot_data = {}
        for ticker in self.newly_fetched_tickers:
            if ticker in self.metadata_cache:
                snapshot_data[ticker] = self.metadata_cache[ticker]
        
        if not snapshot_data:
            return
        
        # 创建快照文件
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        snapshot_dir = os.path.join(self.project_root, 'data', 'company_snapshots')
        os.makedirs(snapshot_dir, exist_ok=True)
        snapshot_file = os.path.join(snapshot_dir, f'company_data_{timestamp}.json')
        
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
        
        self.log(f"[SAVE] 本次分析的公司数据快照已保存: {snapshot_file}")
        return snapshot_file

    def get_stock_metadata(self, ticker, record_new=True):
        """获取股票名称和行业信息 (消除幻觉的关键)"""
        # 1. 先查缓存
        with self.cache_lock:
            if ticker in self.metadata_cache:
                return self.metadata_cache[ticker]['name'], self.metadata_cache[ticker]['sector']

        # 2. 格式转换 (.SH -> .SS 用于 yfinance)
        yf_ticker = ticker.replace(".SH", ".SS") if ".SH" in ticker else ticker
        
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                info = yf.Ticker(yf_ticker).info
                # 优先取中文名或简称，Yahoo A股通常是英文名，AI能翻译
                name = info.get('shortName', info.get('longName', 'Unknown'))
                sector = info.get('sector', info.get('industry', 'Unknown'))
                
                # 如果获取到的信息为空，可能是请求失败，重试
                if not info:
                    self.log(f"[WARN]  获取 {ticker} 信息为空，重试 {attempt+1}/{max_retries}")
                    continue
                
                # 3. 写入缓存（只有当数据有效时）
                if name != 'Unknown':
                    with self.cache_lock:
                        self.metadata_cache[ticker] = {'name': name, 'sector': sector}
                        self._save_cache()
                        # 记录新获取的股票代码
                        if record_new:
                            self.newly_fetched_tickers.add(ticker)
                    
                return name, sector
            except Exception as e:
                self.log(f"[WARN]  获取 {ticker} 元数据失败 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)  # 等待2秒后重试
                else:
                    return "Unknown", "Unknown"
        return "Unknown", "Unknown"

    def load_momentum_data(self, market_type):
        """读取 CSV 并注入元数据"""
        # 更新路径以包含 'micro_report'
        csv_dir = os.path.join(self.project_root, 'micro_report')
        pattern = f"Top200_Momentum_{market_type}_*.csv"
        latest_csv = self.load_latest_file(os.path.join(csv_dir, pattern))
        
        if not latest_csv:
            print(f"[WARN] No CSV found for {market_type} in {csv_dir}")
            return "No data"
            
        df = pd.read_csv(latest_csv)
        # 取前 50 名，避免 Token 溢出，且头部效应最明显
        top_50 = df.head(50) 
        
        print(f"[SEARCH] 正在联网校准 {market_type} 前 50 名股票的业务信息...")
        stock_list_str = []
        
        # 并发获取，避免卡顿
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_ticker = {executor.submit(self.get_stock_metadata, row['ticker']): row for _, row in top_50.iterrows()}
            
            for future in concurrent.futures.as_completed(future_to_ticker):
                row = future_to_ticker[future]
                name, sector = future.result()
                
                # [MODIFIED] 调用统一的格式化函数
                line = self._format_stock_line(row, name, sector)
                stock_list_str.append(line)
        
        return "\n".join(stock_list_str)

    def run_analysis(self, macro_path=None, cn_path=None, us_path=None):
        self.log("[GO] 启动行业趋势分析引擎...")
        
        # 清空本次分析的新获取股票记录
        self.newly_fetched_tickers.clear()
        
        # 1. 准备数据
        if macro_path and os.path.exists(macro_path):
            with open(macro_path, 'r', encoding='utf-8') as f:
                content = f.read()
            risk = "Risk-Off" if "Risk-Off" in content else "Risk-On"
            vol = "Unknown"
            macro_summary = content[:1000]
        else:
            risk, vol, macro_summary = self.load_macro_context()
            
        # Micro CN & US
        if cn_path and os.path.exists(cn_path):
            cn_stocks = self._process_csv(cn_path, 'CN')
        else:
            cn_stocks = self.load_momentum_data('CN')

        if us_path and os.path.exists(us_path):
            us_stocks = self._process_csv(us_path, 'US')
        else:
            us_stocks = self.load_momentum_data('US')
        
        if cn_stocks == "No data" and us_stocks == "No data":
            self.log("[ERR] 缺少动量数据，无法分析")
            return None, None

        # 2. 构建 Prompt (新增最后一段 Metadata 指令)
        prompt = f"""
# Role
你是一位精通全球产业链的资深量化策略分析师。你的任务是基于我提供的"宏观环境"和"市场强势股清单"，通过归纳法推导出当前处于"景气度上行区间"的行业板块。

# Input Data
## 1. Macro Context (宏观背景)
- **Market Status**: {risk} (Risk-On / Risk-Off)
- **Volatility**: {vol}
- **Key Trend**: {macro_summary}

## 2. Micro Evidence (微观资金流向)
**指标说明**:
- **涨幅**: 过去 60 日的价格变化。
- **RSRS (Trend Strength)**: 趋势结构强度指标 (范围 -1.0 ~ 1.0)。
    - **> 0.8 ([HOT])**: 强劲的多头趋势结构（阻力被突破，支撑强劲），代表资金持续流入，**行业逻辑真实性高**。
    - **< 0.3**: 趋势结构松散或处于震荡，单纯的涨幅可能来自短期消息炒作。

**[A-Share Top Momentum]**
{cn_stocks} 

**[US-Share Top Momentum]**
{us_stocks}

# Analysis Requirements
1.  **行业映射**：识别股票代码对应的细分赛道。
2.  **集群识别**：找出出现频次最高的 3-5 个细分行业。
3.  **量化验证 (Critical)**：
    - **不仅仅看涨幅，更要看 RSRS**。
    - 优先筛选出那些**涨幅高且 RSRS > 0.8** 的股票所在的板块。这代表该板块不仅涨了，而且涨得很稳（趋势结构好），是机构资金抱团的特征。
    - 如果某行业股票涨幅大但 RSRS 普遍较低，请在报告中标记为"投机性上涨"。
4.  **宏观验证**：结合宏观背景分析合理性。

# Output Format
请生成一份 Markdown 格式的《行业景气度深度扫描报告》，包含：
1.  **核心结论** (必须包含对 RSRS 确认强度的描述)
2.  **景气度排行** (列出最强行业，并注明其"趋势强度等级")
3.  **产业链映射图谱** (共振逻辑)
4.  **风险提示**

# [STOP] IMPORTANT: Metadata Output
TITLE: [你的标题]
"""
        
        # 3. 调用 API
        self.log("[AI] 正在调用 DeepSeek 进行产业链聚类分析...")
        try:
            response = self.strategist.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are a professional financial analyst."},
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )
            
            raw_content = response.choices[0].message.content
            
            # 确保 raw_content 不是 None
            if raw_content is None:
                raw_content = ""
            
            # --- 核心修改：提取语义化标题 ---
            import re
            title_match = re.search(r"TITLE:\s*(.*)", raw_content)
            
            if title_match:
                # 提取标题
                semantic_title = title_match.group(1).strip()
                # 从正文中移除 TITLE: 行，保持报告整洁
                report_content = raw_content.replace(title_match.group(0), "").strip()
            else:
                # Fallback: 如果没生成，使用默认格式
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
                semantic_title = f"行业全景扫描 ({timestamp})"
                report_content = raw_content
            
            # 确保 report_content 不是 None
            if report_content is None:
                report_content = ""

            # --- 保存文件 (保持时间戳文件名，便于排序) ---
            model_name = self.config.model.replace("/", "-") if self.config.model else "unknown"
            timestamp_file = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filename = f"report_by_{model_name}_{timestamp_file}.md"
            
            save_path = os.path.join(self.project_root, 'research_report', filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            self.log(f"[OK] 行业分析报告已生成: {filename}")
            
            # --- 保存公司数据快照 ---
            self._save_snapshot()
            
            # --- 存入数据库 (使用语义化标题) ---
            self.log(f"[SAVE] 正在自动归档: 《{semantic_title}》")
            
            current_analyst = self.config.model if self.config.model else "deepseek-chat"
            
            save_research_report(
                title=semantic_title,  # <--- 这里存入语义化标题
                content=report_content, 
                tags="Industry, DeepSeek",
                analyst=current_analyst
            )
            
            return report_content, filename
            
        except Exception as e:
            self.log(f"[ERR] 分析过程出错: {e}")
            # 打印详细堆栈以便调试
            import traceback
            traceback.print_exc()
            return None, None

if __name__ == "__main__":
    analyzer = IndustryAnalyzer()
    analyzer.run_analysis()
