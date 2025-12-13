import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QVBoxLayout, 
                             QWidget, QLabel, QComboBox, QHBoxLayout)
from PyQt6.QtGui import QFont

# 路径自适应
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 导入子组件
from scanner_gui import ScannerWidget
from db_editor import DBEditorWidget
from analysis_gui import AnalysisWidget

class CommandCenter(QMainWindow):
    def __init__(self):
        super().__init__()
        # 1. 统一标题
        self.setWindowTitle("MY-DOGE QUANT SYSTEM") 
        self.resize(1000, 700)
        
        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 2. 删除这一段 (原有的大标题)
        # header = QLabel("MY-DOGE QUANT SYSTEM")
        # header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        # ...
        # layout.addWidget(header)
        
        # 标签页容器
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #bdc3c7; }
            QTabBar::tab { padding: 10px; font-weight: bold; }
            QTabBar::tab:selected { background: #3498db; color: white; }
        """)
        layout.addWidget(self.tabs)
        
        # --- 组装 Tab 1: 扫描控制台 ---
        self.scanner_tab = ScannerWidget()
        self.tabs.addTab(self.scanner_tab, "🚀 市场扫描 (Scanner)")
        
        # --- 组装 Tab 2: 档案局 (A股) ---
        self.cn_editor_tab = DBEditorWidget(connection_name="conn_cn_market")
        # 默认加载 A股库
        cn_db_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'data', 'market_data_cn.db')
        self.cn_editor_tab.load_database(cn_db_path) # 假设组件有此方法
        self.tabs.addTab(self.cn_editor_tab, "🇨🇳 A股档案 (CN Data)")
        
        # --- 组装 Tab 3: 档案局 (美股) ---
        self.us_editor_tab = DBEditorWidget(connection_name="conn_us_market")
        us_db_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'data', 'market_data_us.db')
        self.us_editor_tab.load_database(us_db_path)
        self.tabs.addTab(self.us_editor_tab, "🇺🇸 美股档案 (US Data)")
        
        # --- 组装 Tab 4: 研报智库 ---
        self.insight_tab = DBEditorWidget(connection_name="conn_insights")
        insight_db_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), 'data', 'research_insights.db')
        self.insight_tab.load_database(insight_db_path)
        self.tabs.addTab(self.insight_tab, "🧠 研报智库 (Insights)")
        
        # --- 组装 Tab 5: 行业分析台 ---
        self.analysis_tab = AnalysisWidget()
        self.tabs.addTab(self.analysis_tab, "🔎 行业扫描 (Analysis)")
        
        # --- 信号连接：当扫描开始/结束，控制 Tab 状态 ---
        self.scanner_tab.scan_started_signal.connect(self.lock_editor_tab)
        self.scanner_tab.scan_finished_signal.connect(self.unlock_and_refresh)

    def lock_editor_tab(self, mode):
        """扫描开始：禁用对应的 Tab"""
        if mode == 'CN':
            index = self.tabs.indexOf(self.cn_editor_tab)
            self.tabs.setTabEnabled(index, False)
            self.tabs.setTabText(index, "🇨🇳 A股档案 (写入中...)")
        elif mode == 'US':
            index = self.tabs.indexOf(self.us_editor_tab)
            self.tabs.setTabEnabled(index, False)
            self.tabs.setTabText(index, "🇺🇸 美股档案 (写入中...)")

    def unlock_and_refresh(self, mode):
        """扫描结束：启用 Tab 并刷新"""
        if mode == 'CN':
            index = self.tabs.indexOf(self.cn_editor_tab)
            self.tabs.setTabEnabled(index, True)
            self.tabs.setTabText(index, "🇨🇳 A股档案 (CN Data)")
            
            print("🔄 正在刷新 A股档案...")
            self.cn_editor_tab.refresh_data()
            self.tabs.setCurrentWidget(self.cn_editor_tab) # 跳转
            
        elif mode == 'US':
            index = self.tabs.indexOf(self.us_editor_tab)
            self.tabs.setTabEnabled(index, True)
            self.tabs.setTabText(index, "🇺🇸 美股档案 (US Data)")
            
            print("🔄 正在刷新 美股档案...")
            self.us_editor_tab.refresh_data()
            self.tabs.setCurrentWidget(self.us_editor_tab)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = CommandCenter()
    window.show()
    sys.exit(app.exec())
