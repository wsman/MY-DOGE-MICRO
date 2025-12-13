import os
import pandas as pd
import glob
from datetime import datetime
import sys
import yfinance as yf
import concurrent.futures # 用于并发加速获取信息

# --- 路径修复 ---
current_dir = os.path.dirname(os.path.abspath(__file__)) # src/micro
src_dir = os.path.dirname(current_dir)                   # src
project_root = os.path.dirname(src_dir)                  # MY-DOGE-MICRO

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- 导入 ---
try:
    from src.macro.config import MacroConfig
    from src.macro.strategist import DeepSeekStrategist
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")

# 导入数据库保存函数
from database import save_research_report

class IndustryAnalyzer:
    def __init__(self, logger_callback=None):
        self.config = MacroConfig()
        self.strategist = DeepSeekStrategist(self.config)
        self.project_root = project_root
        self.logger_callback = logger_callback

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

    def _process_csv(self, file_path, market_type):
        """处理 CSV 文件并注入元数据（供外部调用）"""
        df = pd.read_csv(file_path)
        # 取前 50 名，避免 Token 溢出，且头部效应最明显
        top_50 = df.head(50) 
        
        self.log(f"🔍 正在联网校准 {market_type} 前 50 名股票的业务信息...")
        stock_list_str = []
        
        # 并发获取，避免卡顿
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(self.get_stock_metadata, row['ticker']): row for _, row in top_50.iterrows()}
            
            for future in concurrent.futures.as_completed(future_to_ticker):
                row = future_to_ticker[future]
                name, sector = future.result()
                
                # 格式：- 605255.SH [Tianpu Stock] (Aerospace) | Change: +465%
                stock_list_str.append(
                    f"- {row['ticker']} [{name}] ({sector}) | 涨幅: +{row['change_percent']}%"
                )
        
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

    def get_stock_metadata(self, ticker):
        """获取股票名称和行业信息 (消除幻觉的关键)"""
        # 1. 格式转换 (.SH -> .SS 用于 yfinance)
        yf_ticker = ticker.replace(".SH", ".SS") if ".SH" in ticker else ticker
        
        try:
            info = yf.Ticker(yf_ticker).info
            # 优先取中文名或简称，Yahoo A股通常是英文名，AI能翻译
            name = info.get('shortName', info.get('longName', 'Unknown'))
            sector = info.get('sector', info.get('industry', 'Unknown'))
            return name, sector
        except:
            return "Unknown", "Unknown"

    def load_momentum_data(self, market_type):
        """读取 CSV 并注入元数据"""
        # 更新路径以包含 'micro_report'
        csv_dir = os.path.join(self.project_root, 'micro_report')
        pattern = f"Top200_Momentum_{market_type}_*.csv"
        latest_csv = self.load_latest_file(os.path.join(csv_dir, pattern))
        
        if not latest_csv:
            print(f"⚠️ No CSV found for {market_type} in {csv_dir}")
            return "No data"
            
        df = pd.read_csv(latest_csv)
        # 取前 50 名，避免 Token 溢出，且头部效应最明显
        top_50 = df.head(50) 
        
        print(f"🔍 正在联网校准 {market_type} 前 50 名股票的业务信息...")
        stock_list_str = []
        
        # 并发获取，避免卡顿
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(self.get_stock_metadata, row['ticker']): row for _, row in top_50.iterrows()}
            
            for future in concurrent.futures.as_completed(future_to_ticker):
                row = future_to_ticker[future]
                name, sector = future.result()
                
                # 格式：- 605255.SH [Tianpu Stock] (Aerospace) | Change: +465%
                stock_list_str.append(
                    f"- {row['ticker']} [{name}] ({sector}) | 涨幅: +{row['change_percent']}%"
                )
        
        return "\n".join(stock_list_str)

    def run_analysis(self, macro_path=None, cn_path=None, us_path=None):
        self.log("🚀 启动行业趋势分析引擎...")
        
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
            self.log("❌ 缺少动量数据，无法分析")
            return None, None

        # 2. 构建 Prompt (新增最后一段 Metadata 指令)
        prompt = f"""
# Role
你是一位精通全球产业链的资深量化策略分析师。你的任务是基于我提供的“宏观环境”和“市场强势股清单”，通过归纳法推导出当前处于“景气度上行区间”的行业板块。

# Input Data
## 1. Macro Context (宏观背景)
- **Market Status**: {risk} (Risk-On / Risk-Off)
- **Volatility**: {vol}
- **Key Trend**: {macro_summary}

## 2. Micro Evidence (微观资金流向)
**[A-Share Top Momentum]**
{cn_stocks} 

**[US-Share Top Momentum]**
{us_stocks}

# Analysis Requirements
1.  **行业映射**：识别股票代码对应的细分赛道。
2.  **集群识别**：找出出现频次最高的 3-5 个细分行业。
3.  **宏观验证**：结合宏观背景分析合理性。

# Output Format
请生成一份 Markdown 格式的《行业景气度深度扫描报告》，包含：
1.  **核心结论**
2.  **景气度排行** (列出最强行业)
3.  **产业链映射图谱** (共振逻辑)
4.  **风险提示**

# 🛑 IMPORTANT: Metadata Output
在报告的**最后一行**，请务必根据报告核心结论，生成一个简短、专业的中文标题（20字以内），格式必须严格如下：
TITLE: [你的标题]
(例如: TITLE: 避险情绪主导，黄金与军工板块成全球共振主线)
"""
        
        # 3. 调用 API
        self.log("🧠 正在调用 DeepSeek 进行产业链聚类分析...")
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

            # --- 保存文件 (保持时间戳文件名，便于排序) ---
            model_name = self.config.model.replace("/", "-") if self.config.model else "unknown"
            timestamp_file = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filename = f"report_by_{model_name}_{timestamp_file}.md"
            
            save_path = os.path.join(self.project_root, 'research_report', filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            self.log(f"✅ 行业分析报告已生成: {filename}")
            
            # --- 存入数据库 (使用语义化标题) ---
            self.log(f"💾 正在自动归档: 《{semantic_title}》")
            
            current_analyst = self.config.model if self.config.model else "deepseek-chat"
            
            save_research_report(
                title=semantic_title,  # <--- 这里存入语义化标题
                content=report_content, 
                tags="Industry, DeepSeek",
                analyst=current_analyst
            )
            
            return report_content, filename
            
        except Exception as e:
            self.log(f"❌ 分析过程出错: {e}")
            # 打印详细堆栈以便调试
            import traceback
            traceback.print_exc()
            return None, None

if __name__ == "__main__":
    analyzer = IndustryAnalyzer()
    analyzer.run_analysis()
