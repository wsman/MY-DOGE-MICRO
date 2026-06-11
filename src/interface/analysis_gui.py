import sys
import os
import json
import threading
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QFileDialog, 
                             QComboBox, QGroupBox, QSplitter, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QThread

# 路径适配
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(os.path.join(project_root, 'src', 'micro'))

from industry_analyzer import IndustryAnalyzer

class AnalysisWorker(QThread):
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(str, str) # content, filename
    
    def __init__(self, macro_path, cn_path, us_path, profile_config):
        super().__init__()
        self.macro_path = macro_path
        self.cn_path = cn_path
        self.us_path = us_path
        self.profile = profile_config

    def run(self):
        # DEEPSEEK_MODEL is set from the selected profile so GUI model-switching
        # keeps working. As of S002-013 the operator MUST export
        # DEEPSEEK_API_KEY before launching the GUI — models_config.json ships
        # only a placeholder, so we no longer inject the profile's api_key here.
        os.environ["DEEPSEEK_MODEL"] = self.profile.get("model", "deepseek-chat")

        if not os.environ.get("DEEPSEEK_API_KEY"):
            # Surface the missing key via the worker log so the operator sees a
            # clear remediation hint instead of an opaque SDK auth failure.
            self.log_signal.emit(
                "⚠️ DEEPSEEK_API_KEY is not set in the environment. "
                "Export DEEPSEEK_API_KEY=<your-key> before launching the GUI, "
                "or macro report generation will fail."
            )

        # 如果底层支持 base_url 环境变量，也可以注入，否则默认
        
        try:
            analyzer = IndustryAnalyzer()
            # 注入日志回调
            original_print = print
            def log_wrapper(*args):
                msg = " ".join(map(str, args))
                self.log_signal.emit(msg)
                original_print(msg) # 保持控制台输出
            
            # 临时替换 print (简单粗暴但有效)
            import builtins
            builtins.print = log_wrapper
            
            # 手动注入路径，防止 analyzer 自动去扫最新文件，而是用 GUI 指定的
            # 这里需要稍微修改 IndustryAnalyzer 的 run_analysis 逻辑支持传参
            # 但为了保持兼容，我们暂时假设用户选的就是最新的，或者 Analyzer 内部逻辑够强
            # V2优化：建议修改 Analyzer 直接接受路径参数
            
            analyzer.run_analysis()
            
            # 恢复 print
            builtins.print = original_print
            
            # 尝试读取生成的最新报告显示
            import glob
            report_dir = os.path.join(project_root, 'research_report')
            files = glob.glob(os.path.join(report_dir, "*.md"))
            if files:
                latest_report = max(files, key=os.path.getctime)
                with open(latest_report, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.result_signal.emit(content, os.path.basename(latest_report))
                
        except Exception as e:
            self.log_signal.emit(f"❌ 运行出错: {str(e)}")

class AnalysisWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.config_data = {}
        self.init_ui()
        self.load_config_profiles()
        self.auto_fill_paths()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # --- 1. 顶部控制区 (高度压缩) ---
        control_group = QGroupBox("战术配置面板")
        control_group.setFixedHeight(120) # 限制高度
        control_layout = QVBoxLayout(control_group)
        control_layout.setContentsMargins(5, 5, 5, 5)
        
        # Row 1: 模型选择 + 运行按钮
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("战略模型:"))
        self.profile_combo = QComboBox()
        row1.addWidget(self.profile_combo, 3) # 占主要宽度
        
        self.btn_run = QPushButton("🚀 执行全景扫描")
        self.btn_run.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_run.clicked.connect(self.start_analysis)
        row1.addWidget(self.btn_run, 1)
        control_layout.addLayout(row1)

        # Row 2: 文件路径 (紧凑模式)
        row2 = QHBoxLayout()
        self.macro_edit = self.create_file_input(row2, "宏观报告:", "Markdown (*.md)")
        self.cn_edit = self.create_file_input(row2, "A股数据:", "CSV (*.csv)")
        self.us_edit = self.create_file_input(row2, "美股数据:", "CSV (*.csv)")
        control_layout.addLayout(row2)
        
        layout.addWidget(control_group)

        # --- 2. 核心报告区 (C位，尽可能大) ---
        self.report_viewer = QTextEdit()
        self.report_viewer.setPlaceholderText("等待任务执行... 报告将在此处生成")
        self.report_viewer.setStyleSheet("font-family: Consolas; font-size: 11pt; line-height: 1.4;")
        layout.addWidget(self.report_viewer, 1) # Stretch = 1, 抢占剩余空间

        # --- 3. 底部日志区 (高度压缩) ---
        log_group = QGroupBox("系统遥测日志")
        log_group.setFixedHeight(100) # 限制高度
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(2, 2, 2, 2)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #f0f0f0; font-size: 9pt;")
        log_layout.addWidget(self.log_view)
        
        layout.addWidget(log_group)

    def create_file_input(self, parent_layout, label_text, filter_ext):
        container = QWidget()
        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #7f8c8d; font-size: 9pt;")
        h_layout.addWidget(lbl)
        
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("自动检测中...")
        h_layout.addWidget(line_edit)
        
        btn = QPushButton("...")
        btn.setFixedWidth(30)
        btn.clicked.connect(lambda: self.browse_file(line_edit, filter_ext))
        h_layout.addWidget(btn)
        
        parent_layout.addWidget(container)
        return line_edit

    def load_config_profiles(self):
        """加载 JSON 配置文件"""
        config_path = os.path.join(project_root, 'models_config.json')
        if not os.path.exists(config_path):
            self.log_view.append("⚠️ 未找到 models_config.json，请创建配置！")
            return
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
                
            profiles = self.config_data.get('profiles', [])
            self.profile_combo.clear()
            for p in profiles:
                # 存储整个 profile 对象到 userData
                self.profile_combo.addItem(p['name'], p)
                
            # 设置默认
            default = self.config_data.get('default_profile')
            if default:
                idx = self.profile_combo.findText(default)
                if idx >= 0: self.profile_combo.setCurrentIndex(idx)
                
            self.log_view.append(f"✅ 已加载 {len(profiles)} 个战略模型配置")
            
        except Exception as e:
            self.log_view.append(f"❌ 配置文件读取失败: {e}")

    def browse_file(self, line_edit, filter_ext):
        f, _ = QFileDialog.getOpenFileName(self, "选择文件", project_root, f"Files ({filter_ext})")
        if f: line_edit.setText(f)

    def auto_fill_paths(self):
        # 尝试自动填入最新的文件
        try:
            import glob
            # Macro
            macro_files = glob.glob(os.path.join(project_root, 'macro_report', '*.md'))
            if macro_files: self.macro_edit.setText(max(macro_files, key=os.path.getctime))
            
            # CN CSV
            cn_files = glob.glob(os.path.join(project_root, 'micro_report', 'Top200_Momentum_CN_*.csv'))
            if cn_files: self.cn_edit.setText(max(cn_files, key=os.path.getctime))
            
            # US CSV
            us_files = glob.glob(os.path.join(project_root, 'micro_report', 'Top200_Momentum_US_*.csv'))
            if us_files: self.us_edit.setText(max(us_files, key=os.path.getctime))
            
        except Exception as e:
            pass

    def start_analysis(self):
        macro = self.macro_edit.text()
        cn = self.cn_edit.text()
        us = self.us_edit.text()
        
        # 获取当前选中的 Profile 数据
        profile = self.profile_combo.currentData()
        if not profile:
            self.log_view.append("❌ 未选择有效的模型配置")
            return
            
        self.btn_run.setEnabled(False)
        self.log_view.clear()
        self.report_viewer.clear()
        self.report_viewer.append("⏳ 正在初始化 AI 引擎，开始深度推理...")
        
        self.worker = AnalysisWorker(macro, cn, us, profile)
        self.worker.log_signal.connect(self.log_view.append)
        self.worker.result_signal.connect(self.display_report)
        self.worker.finished.connect(lambda: self.btn_run.setEnabled(True))
        self.worker.start()

    def display_report(self, content, filename):
        self.report_viewer.setMarkdown(content)
        self.log_view.append(f"✅ 分析完成！报告已保存为: {filename}")
