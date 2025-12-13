import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def get_db_connection(db_path=None):
    """获取数据库连接对象
    
    Args:
        db_path (str): 数据库文件路径，如果为 None，则使用默认路径 'data/market_data.db'
        
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    if db_path is None:
        db_path = 'data/market_data.db'
    
    # 确保目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)


# 初始化主数据库
def init_db():
    """初始化数据库，创建 stock_prices 表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 删除旧表（如果存在）
    cursor.execute('DROP TABLE IF EXISTS stock_prices')
    
    # 创建 stock_prices 表，包含复合主键 (ticker, date)
    cursor.execute('''
        CREATE TABLE stock_prices (
            ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            amount REAL,
            PRIMARY KEY (ticker, date)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

# 初始化AI研报数据库
def init_research_db():
    """初始化AI研报数据库，创建 insights 表"""
    conn = sqlite3.connect('data/research_insights.db')
    cursor = conn.cursor()
    
    # 创建 insights 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            category TEXT,
            target TEXT,
            summary TEXT,
            full_content TEXT
        )
    ''')
    
    # 创建知识实体表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            entity_type TEXT
        )
    ''')
    
    # 创建知识图谱关系表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_graph (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            target TEXT,
            relation TEXT,
            insight_id INTEGER,
            FOREIGN KEY (insight_id) REFERENCES insights(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ AI研报数据库初始化完成")

def init_db_custom(db_path):
    """使用指定路径初始化数据库，创建 stock_prices 表（仅当表不存在时）"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # 创建 stock_prices 表，包含复合主键 (ticker, date)，不删除旧表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_prices (
            ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            amount REAL,
            PRIMARY KEY (ticker, date)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成: {db_path}")

def save_stock_data_custom(data, db_path):
    """将股票数据保存到指定数据库
    
    Args:
        data (pd.DataFrame): 包含股票数据的 DataFrame
        db_path (str): 目标数据库路径
    """
    conn = get_db_connection(db_path)
    
    try:
        # 使用 to_sql 方法批量插入数据，if_exists='append' 表示追加模式
        data.to_sql('stock_prices', conn, if_exists='append', index=False)
        print(f"💾 数据已保存到数据库: {db_path}")
    except Exception as e:
        print(f"❌ 保存数据时出错: {e}")
    finally:
        conn.close()

def _ensure_columns(cursor, table_name, new_columns):
    """
    辅助函数：检查并自动添加缺失的列 (自动迁移)
    new_columns: list of (col_name, col_type)
    """
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_cols = [info[1] for info in cursor.fetchall()]
    
    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            print(f"🔄 正在迁移表 {table_name}: 添加列 {col_name}...")
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                print(f"⚠️ 迁移警告: {e}")

def save_macro_report(content, risk_signal, volatility, tags="Macro, DeepSeek", analyst="deepseek-reasoner"):
    """
    将宏观策略报告归档到数据库 (Schema V2)
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'research_insights.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    table_name = "macro_reports"
    
    # 1. 确保表存在 (V2 结构) - 修改列顺序
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            timestamp TEXT,
            tags TEXT,
            analyst TEXT,
            risk_signal TEXT,
            volatility TEXT,
            content TEXT
        )
    ''')
    
    # 2. 自动迁移：检查旧表是否缺少新列
    _ensure_columns(cursor, table_name, [("tags", "TEXT"), ("analyst", "TEXT")])
    
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    try:
        cursor.execute(
            f"INSERT INTO {table_name} (date, timestamp, tags, analyst, risk_signal, volatility, content) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (date_str, time_str, tags, analyst, risk_signal, volatility, content)
        )
        conn.commit()
        print(f"✅ 宏观报告已归档 (Analyst: {analyst})")
    except Exception as e:
        print(f"❌ 宏观报告归档失败: {e}")
    finally:
        conn.close()

def save_research_report(title, content, tags="Industry, DeepSeek", analyst="deepseek-chat"):
    """
    将行业研报归档到数据库 (Schema V2 - 对齐 Macro 表格式)
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'research_insights.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    table_name = "research_reports"
    
    # 1. 确保表存在 (V2 结构: 增加 timestamp, analyst) - 修改列顺序
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            timestamp TEXT,
            tags TEXT,
            analyst TEXT,
            title TEXT,
            content TEXT
        )
    ''')
    
    # 2. 自动迁移
    _ensure_columns(cursor, table_name, [("timestamp", "TEXT"), ("analyst", "TEXT"), ("tags", "TEXT")])
    
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    try:
        cursor.execute(
            f"INSERT INTO {table_name} (date, timestamp, tags, analyst, title, content) VALUES (?, ?, ?, ?, ?, ?)",
            (date_str, time_str, tags, analyst, title, content)
        )
        conn.commit()
        print(f"✅ 行业研报已归档 (Analyst: {analyst})")
    except Exception as e:
        print(f"❌ 研报归档失败: {e}")
    finally:
        conn.close()

def save_insight(category, target, summary, full_content):
    """
    保存AI研报到数据库
    
    Args:
        category (str): 研报类别
        target (str): 目标股票或主题
        summary (str): 摘要
        full_content (str): 完整内容
    """
    conn = sqlite3.connect('data/research_insights.db')
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO insights (created_at, category, target, summary, full_content)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), category, target, summary, full_content))
        
        conn.commit()
        print(f"💾 AI研报已保存到数据库")
    except Exception as e:
        print(f"❌ 保存AI研报时出错: {e}")
    finally:
        conn.close()

def get_history_insights(limit=None, category=None, target=None):
    """
    获取历史AI研报
    
    Args:
        limit (int): 返回记录数限制
        category (str): 筛选类别（可选）
        target (str): 筛选目标（可选）
        
    Returns:
        list: 研报列表
    """
    conn = sqlite3.connect('data/research_insights.db')
    
    try:
        cursor = conn.cursor()
        
        # 构建查询条件
        query = 'SELECT * FROM insights WHERE 1=1'
        params = []
        
        if category:
            query += ' AND category = ?'
            params.append(category)
            
        if target:
            query += ' AND target = ?'
            params.append(target)
            
        query += ' ORDER BY created_at DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 转换为字典列表
        columns = [description[0] for description in cursor.description]
        insights = [dict(zip(columns, row)) for row in rows]
        
        return insights
    except Exception as e:
        print(f"❌ 查询AI研报时出错: {e}")
        return []
    finally:
        conn.close()

def add_entity(name, entity_type):
    """
    添加知识实体
    
    Args:
        name (str): 实体名称
        entity_type (str): 实体类型
    """
    conn = sqlite3.connect('data/research_insights.db')
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO knowledge_entities (name, entity_type)
            VALUES (?, ?)
        ''', (name, entity_type))
        
        conn.commit()
        if cursor.rowcount > 0:
            print(f"💾 实体 '{name}' 已添加到知识库")
        else:
            print(f"⚠️ 实体 '{name}' 已存在，跳过添加")
    except Exception as e:
        print(f"❌ 添加实体时出错: {e}")
    finally:
        conn.close()

def add_relationship(source, target, relation, insight_id):
    """
    添加知识图谱关系
    
    Args:
        source (str): 起点实体名
        target (str): 终点实体名
        relation (str): 关系描述
        insight_id (int): 关联的研报ID
    """
    conn = sqlite3.connect('data/research_insights.db')
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO knowledge_graph (source, target, relation, insight_id)
            VALUES (?, ?, ?, ?)
        ''', (source, target, relation, insight_id))
        
        conn.commit()
        print(f"🔗 关系 '{source} -> {relation} -> {target}' 已添加到知识图谱")
    except Exception as e:
        print(f"❌ 添加关系时出错: {e}")
    finally:
        conn.close()
