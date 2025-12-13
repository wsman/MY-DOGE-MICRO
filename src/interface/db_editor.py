import sys
import os
from PyQt6.QtWidgets import (
    QWidget, QTableView, QVBoxLayout, 
    QPushButton, QFileDialog, QComboBox, 
    QMessageBox, QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox,
    QHBoxLayout, QLabel
)
from PyQt6.QtSql import QSqlDatabase, QSqlTableModel, QSqlField
from PyQt6.QtCore import Qt, QSize, QEvent
import datetime

class AddRecordDialog(QDialog):
    def __init__(self, table_name, db, parent=None):
        super().__init__(parent)
        self.table_name = table_name
        self.db = db
        self.setWindowTitle(f"添加记录 - {table_name}")
        self.resize(600, 400)
        
        # 获取表结构
        self.model = QSqlTableModel(self, db)
        self.model.setTable(table_name)
        self.model.select()
        
        layout = QVBoxLayout()
        
        # 创建表单布局
        form_layout = QFormLayout()
        
        # 存储控件以供后续访问
        self.field_widgets = {}
        
        # 获取字段信息
        record = self.model.record(0) if self.model.rowCount() > 0 else self.model.record()
        
        for i in range(record.count()):
            field_name = record.fieldName(i)
            field_value = record.value(i)
            
            # 创建控件（根据表名和字段名进行优化）
            widget = None
            
            # 特别处理 insights 表的 full_content 字段
            if table_name == 'insights' and field_name == 'full_content':
                # 使用 QTextEdit 而不是 QLineEdit，方便编辑大文本
                widget = QTextEdit()
                widget.setMaximumHeight(150)  # 设置最大高度
                
                # 添加文件导入按钮
                button_layout = QHBoxLayout()
                file_button = QPushButton("📂 从文件导入 (MD/TXT)")
                file_button.clicked.connect(lambda _, w=widget: self.import_file(w))
                button_layout.addWidget(file_button)
                button_layout.addStretch()
                
                form_layout.addRow(QLabel(f"{field_name}:"), widget)
                form_layout.addRow(button_layout)
            else:
                # 对于其他字段，使用 QLineEdit
                if field_name == 'created_at':
                    # 自动填充当前时间并禁用编辑
                    widget = QLineEdit()
                    widget.setText(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    widget.setReadOnly(True)
                else:
                    widget = QLineEdit()
                
                form_layout.addRow(QLabel(f"{field_name}:"), widget)
            
            self.field_widgets[field_name] = widget
        
        layout.addLayout(form_layout)
        
        # 添加按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def import_file(self, text_edit):
        """导入文件内容到文本框"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择文件",
            "",
            "Markdown Files (*.md);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查文本框是否已有内容
                existing_content = text_edit.toPlainText()
                if existing_content.strip():
                    reply = QMessageBox.question(
                        self,
                        "文件导入",
                        "文本框中已存在内容，选择操作：\n\n覆盖现有内容或追加到现有内容？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:  # 覆盖
                        text_edit.setPlainText(content)
                    elif reply == QMessageBox.StandardButton.No:  # 追加
                        text_edit.setText(existing_content + '\n\n' + content)
                else:
                    text_edit.setPlainText(content)
                    
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取文件时出错：{str(e)}")

class DBEditorWidget(QWidget):
    def __init__(self, connection_name=None):
        super().__init__()
        
        # 初始化数据库连接（但不立即创建）
        self.db = None
        if connection_name:
            self.connection_name = connection_name
        else:
            self.connection_name = f"conn_{id(self)}"
        self.current_db_path = None
        self.current_table_model = None
        
        # 创建界面
        self.create_ui()
    
    def clear_model(self):
        """清理当前模型，释放对数据库连接的引用"""
        if self.current_table_model:
            # 先断开视图与模型的关联
            self.table_view.setModel(None)
            # 删除模型（Python 会自动回收）
            self.current_table_model = None
    
    def create_ui(self):
        layout = QVBoxLayout(self) # 直接应用到 self
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        open_db_button = QPushButton("📂 打开数据库")
        open_db_button.clicked.connect(self.open_database)
        toolbar_layout.addWidget(open_db_button)
        
        self.table_combo = QComboBox()
        self.table_combo.currentTextChanged.connect(self.on_table_changed)
        toolbar_layout.addWidget(QLabel("选择表:"))
        toolbar_layout.addWidget(self.table_combo)
        
        refresh_button = QPushButton("🔄 刷新")
        refresh_button.clicked.connect(self.refresh_data)
        toolbar_layout.addWidget(refresh_button)
        
        save_button = QPushButton("💾 保存更改")
        save_button.clicked.connect(self.save_changes)
        toolbar_layout.addWidget(save_button)
        
        layout.addLayout(toolbar_layout)
        
        # 表视图
        self.table_view = QTableView()
        self.table_view.setEditTriggers(QTableView.EditTrigger.DoubleClicked | QTableView.EditTrigger.SelectedClicked)
        layout.addWidget(self.table_view)
        
        # 操作栏
        action_layout = QHBoxLayout()
        
        add_button = QPushButton("➕ 添加记录")
        add_button.clicked.connect(self.add_record)
        action_layout.addWidget(add_button)
        
        delete_button = QPushButton("🗑️ 删除选中")
        delete_button.clicked.connect(self.delete_selected)
        action_layout.addWidget(delete_button)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索...")
        self.search_input.textChanged.connect(self.apply_search_filter)
        action_layout.addWidget(QLabel("搜索:"))
        action_layout.addWidget(self.search_input)
        
        layout.addLayout(action_layout)
    
    def load_database(self, db_path):
        """加载指定的数据库文件（连接复用版）"""
        # 清理现有模型
        self.clear_model()

        # 检查是否已有同名连接存在
        if QSqlDatabase.contains(self.connection_name):
            self.db = QSqlDatabase.database(self.connection_name)
            # 如果路径变了，才需要重新设置数据库路径
            if self.db.databaseName() != db_path:
                self.db.close()
                self.db.setDatabaseName(db_path)
        else:
            # 创建新的数据库连接
            self.db = QSqlDatabase.addDatabase("QSQLITE", self.connection_name)
            self.db.setDatabaseName(db_path)

        self.current_db_path = db_path

        # 打开数据库（如果未打开）
        if not self.db.isOpen():
            if not self.db.open():
                QMessageBox.critical(self, "错误", f"无法打开数据库文件:\n{self.db.lastError().text()}")
                return

        # 加载表列表
        self.load_tables()
    
    def open_database(self):
        """打开数据库文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 SQLite 数据库文件",
            "",
            "SQLite Database Files (*.db *.sqlite);;All Files (*)"
        )
        
        if file_path:
            self.load_database(file_path)
    
    def load_tables(self):
        """加载所有表名"""
        try:
            # 使用正确的 API 获取表名
            table_names = self.db.tables()
            self.table_combo.clear()
            self.table_combo.addItems(table_names)
            
            if table_names:
                self.on_table_changed(table_names[0])
            else:
                QMessageBox.information(self, "提示", "数据库中没有表。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载表列表时出错：{str(e)}")
    
    def on_table_changed(self, table_name):
        """当选择的表发生变化"""
        if not table_name or not self.db or not self.db.isOpen():
            return
        
        # 清理现有模型
        self.clear_model()
        
        # 创建模型并设置
        self.current_table_model = QSqlTableModel(self, self.db)
        self.current_table_model.setTable(table_name)
        
        try:
            self.current_table_model.select()
            
            # 设置视图
            self.table_view.setModel(self.current_table_model)
            
            # 调整列宽以适应内容
            self.table_view.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载表数据时出错：{str(e)}")
    
    def refresh_data(self):
        """刷新当前数据显示"""
        if self.current_table_model:
            try:
                self.current_table_model.select()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"刷新数据时出错：{str(e)}")
    
    def save_changes(self):
        """保存更改到数据库"""
        if not self.current_table_model:
            return
            
        try:
            # 提交所有未提交的更改
            if self.current_table_model.submitAll():
                QMessageBox.information(self, "成功", "数据已成功保存！")
                self.refresh_data()
            else:
                QMessageBox.critical(self, "错误", f"保存失败：\n{self.current_table_model.lastError().text()}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存时出错：{str(e)}")
    
    def add_record(self):
        """添加新记录"""
        if not self.table_combo.currentText():
            QMessageBox.warning(self, "警告", "请先选择一个表。")
            return
            
        table_name = self.table_combo.currentText()
        
        dialog = AddRecordDialog(table_name, self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 重新加载数据
            self.refresh_data()
    
    def delete_selected(self):
        """删除选中的记录"""
        if not self.current_table_model:
            return
            
        selection = self.table_view.selectionModel().selectedRows()
        if not selection:
            QMessageBox.warning(self, "警告", "请先选择要删除的行。")
            return
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除 {len(selection)} 行记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 从后往前删除以避免索引变化问题
                for row in sorted([index.row() for index in selection], reverse=True):
                    self.current_table_model.removeRow(row)
                
                # 提交更改
                if self.current_table_model.submitAll():
                    QMessageBox.information(self, "成功", "记录已成功删除！")
                    self.refresh_data()
                else:
                    QMessageBox.critical(self, "错误", f"删除失败：\n{self.current_table_model.lastError().text()}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除时出错：{str(e)}")
    
    def apply_search_filter(self):
        """应用搜索过滤"""
        text = self.search_input.text()
        if not self.current_table_model:
            return
        if not text:
            # 如果没有文本，清除过滤器
            self.current_table_model.setFilter("")
            return
            
        try:
            # 简单实现：对第一个字段进行模糊匹配（实际项目中应更智能）
            field_name = None
            record = self.current_table_model.record(0) if self.current_table_model.rowCount() > 0 else self.current_table_model.record()
            
            # 对所有字段使用第一个字段（简单实现）
            if record.count() > 0:
                field_name = record.fieldName(0)
            
            if field_name:
                filter_str = f"{field_name} LIKE '%{text}%'"  
                self.current_table_model.setFilter(filter_str)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用过滤器时出错：{str(e)}")

    def closeEvent(self, event):
        """窗口关闭时清理数据库连接"""
        # 清理模型
        self.clear_model()
        
        # 关闭并移除数据库连接
        if self.db:
            if self.db.isOpen():
                self.db.close()
            QSqlDatabase.removeDatabase(self.connection_name)
            
        super().closeEvent(event)
