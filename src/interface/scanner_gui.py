import sys
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFileDialog, QGroupBox, QTextEdit, QProgressBar, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal

# --- 路径修复核心代码 ---
# 1. 获取关键目录路径
current_file_path = os.path.abspath(__file__)
interface_dir = os.path.dirname(current_file_path)  # .../src/interface
src_dir = os.path.dirname(interface_dir)            # .../src
project_root = os.path.dirname(src_dir)             # .../MY-DOGE-MICRO

# 2. 将项目根目录加入 sys.path (确保优先级)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 3. 导入核心模块 (使用全限定路径)
try:
    # 导入 Micro 模块
    from src.micro.market_scanner import MarketScanner
    
    # 导入 Macro 模块 (这是之前报错的地方)
    from src.macro.config import MacroConfig
    from src.macro.data_loader import GlobalMacroLoader
    from src.macro.strategist import DeepSeekStrategist
except ImportError as e:
    print(f"❌ 严重导入错误: {e}")
    print("请确保项目目录下存在 __init__.py 文件，且目录结构正确。")
    # 为了防止IDE报错干扰，这里可以保留一个备用尝试，但通常根目录导入是最稳的
# ------------------------

class MacroWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def run(self):
        self.log_signal.emit("🌍 启动宏观战略分析 (Macro Scan)...")
        try:
            # 1. 加载配置
            config = MacroConfig()

            # 2. 获取数据
            # [修正 1] 修改日志文案，将 A50 改为 沪深300
            self.log_signal.emit("📡 正在同步全球市场数据 (QQQ, GLD, BTC, 沪深300)...")
            loader = GlobalMacroLoader(config)
            market_data = loader.fetch_combined_data()

            if market_data is not None:
                # 3. 计算指标
                metrics = loader.calculate_metrics(market_data)

                # 4. DeepSeek 推理
                self.log_signal.emit(f"🧠 正在调用 {config.model} 进行宏观定调...")
                strategist = DeepSeekStrategist(config)
                # 生成并保存报告 (generate_strategy_report 内部已包含保存逻辑)
                raw_report = strategist.generate_strategy_report(metrics, market_data)
                
                # [修正点] 自动入库逻辑 - 显式传入 model 名称
                self.log_signal.emit("💾 正在归档宏观战略报告...")
                
                # 提取关键指标用于索引
                risk_str = "Risk-On" if metrics.get('risk_on_signal') else "Risk-Off"
                vol_val = metrics.get('tech_volatility', 0)
                vol_str = f"{vol_val:.2f}%" if isinstance(vol_val, (int, float)) else str(vol_val)
                
                # 局部导入以避免循环依赖
                try:
                    from src.micro.database import save_macro_report
                    save_macro_report(raw_report, risk_str, vol_str, analyst=config.model)  # <--- 关键修改：传入实际模型名
                except ImportError:
                    # 尝试从根路径导入
                    import sys
                    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src', 'micro'))
                    from database import save_macro_report
                    save_macro_report(raw_report, risk_str, vol_str, analyst=config.model)  # <--- 关键修改：传入实际模型名

                self.log_signal.emit("✅ 宏观分析完成！报告已生成并归档。")
            else:
                self.log_signal.emit("❌ 数据获取失败")
                
        except Exception as e:
            self.log_signal.emit(f"❌ 宏观分析出错: {str(e)}")
        
        self.finished_signal.emit()

class ScannerWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    scan_finished_signal = pyqtSignal(str)  # 添加此行以定义信号
    
    def __init__(self, mode, tdx_path, db_path):
        super().__init__()
        self.mode = mode
        self.tdx_path = tdx_path
        self.db_path = db_path

    def run(self):
        self.log_signal.emit(f"🚀 开始任务: {self.mode} 扫描")
        self.log_signal.emit(f"📂 数据源: {self.tdx_path}")
        self.log_signal.emit(f"💾 目标库: {self.db_path}")
        
        try:
            scanner = MarketScanner(self.tdx_path)
            
            def callback(pct, msg):
                self.progress_signal.emit(pct, msg)
                
            if self.mode == 'CN':
                scanner.scan_cn_market(self.db_path, callback)
            elif self.mode == 'US':
                scanner.scan_us_market(self.db_path, callback)
                
            self.log_signal.emit("✅ 扫描任务完成！")
            self.progress_signal.emit(100, "完成")
            
        except Exception as e:
            self.log_signal.emit(f"❌ 发生错误: {str(e)}")
        finally:
            # 在任务结束后发射扫描完成信号
            self.scan_finished_signal.emit(self.mode)

class ScannerWidget(QWidget):
    # 自定义信号：扫描开始和完成时发射模式（'CN' 或 'US'）
    scan_started_signal = pyqtSignal(str)
    scan_finished_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MY-DOGE 数据中台控制室")
        self.resize(600, 500)
        
        # 创建界面
        self.create_ui()
        
    def create_ui(self):
        layout = QVBoxLayout(self) # 直接应用到 self
        
        # 1. 基础配置
        config_group = QGroupBox("基础配置")
        config_layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        self.tdx_path_edit = QLineEdit(r"D:\Games\New Tdx Vip2020") # 默认值
        path_layout.addWidget(QLabel("TDX根目录:"))
        path_layout.addWidget(self.tdx_path_edit)
        btn_tdx = QPushButton("浏览")
        btn_tdx.clicked.connect(self.select_tdx_dir)
        path_layout.addWidget(btn_tdx)
        config_layout.addLayout(path_layout)
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # 2. 战区控制
        action_group = QGroupBox("扫描控制")
        action_layout = QHBoxLayout()
        
        # A股按钮
        self.btn_cn = QPushButton("启动 A股扫描 (CN)")
        self.btn_cn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 10px;")
        self.btn_cn.clicked.connect(lambda: self.start_scan('CN'))
        action_layout.addWidget(self.btn_cn)
        
        # 美股按钮
        self.btn_us = QPushButton("启动 美股扫描 (US)")
        self.btn_us.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 10px;")
        self.btn_us.clicked.connect(lambda: self.start_scan('US'))
        action_layout.addWidget(self.btn_us)
        
        action_group.setLayout(action_layout)
        layout.addWidget(action_group)
        
        # 添加宏观分析按钮
        self.btn_macro = QPushButton("启动宏观分析")
        self.btn_macro.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 10px;")
        self.btn_macro.clicked.connect(self.start_macro_scan)
        action_layout.addWidget(self.btn_macro)
        
        # 3. 进度与日志
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)
        
    def select_tdx_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择通达信根目录")
        if path: self.tdx_path_edit.setText(path)
            
    def start_scan(self, mode):
        tdx_root = self.tdx_path_edit.text()
        # 自动决定数据库路径
        db_name = "market_data_cn.db" if mode == 'CN' else "market_data_us.db"
        # 假设 data 目录在项目根目录
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', db_name)
        
        # 1. 界面锁定：禁用两个按钮，防止重复点击
        self.btn_cn.setEnabled(False)
        self.btn_us.setEnabled(False)
        self.log_view.append(f"🔒 锁定界面，开始 {mode} 扫描...")
        
        # 2. 发送扫描开始信号给主窗口
        self.scan_started_signal.emit(mode)
        
        self.worker = ScannerWorker(mode, tdx_root, db_path)
        self.worker.log_signal.connect(self.log_view.append)
        self.worker.progress_signal.connect(self.update_progress)
        # 连接 worker 完成信号到内部处理函数（用于恢复按钮状态）
        self.worker.scan_finished_signal.connect(lambda: self.on_worker_finished(mode))
        self.worker.start()
        

    def update_progress(self, val, msg):
        self.progress_bar.setValue(val)
        self.status_label.setText(msg)

    def on_worker_finished(self, mode):
        """工作线程完成后的内部处理：恢复按钮状态"""
        self.btn_cn.setEnabled(True)
        self.btn_us.setEnabled(True)
        self.log_view.append("🔓 扫描结束，界面解锁。")
        # 转发信号给主窗口去刷新 Tab
        self.scan_finished_signal.emit(mode)

    def start_macro_scan(self):
        # 禁用所有扫描按钮
        self.btn_cn.setEnabled(False)
        self.btn_us.setEnabled(False)
        self.btn_macro.setEnabled(False)
        self.log_view.append("🌍 开始宏观分析...")

        self.macro_worker = MacroWorker()
        self.macro_worker.log_signal.connect(self.log_view.append)
        self.macro_worker.finished_signal.connect(self.on_macro_finished)
        self.macro_worker.start()

    def on_macro_finished(self):
        self.btn_cn.setEnabled(True)
        self.btn_us.setEnabled(True)
        self.btn_macro.setEnabled(True)
        self.log_view.append("✅ 宏观分析完成，界面解锁。")
