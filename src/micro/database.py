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
    print("[OK] database initialized")

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
    print("[OK] AI research database initialized")

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
    print(f"[OK] database initialized: {db_path}")

def save_stock_data_custom(data, db_path, retention_days=None):
    """增量写入 + 自动清理超过 retention_days 的旧数据

    Args:
        data (pd.DataFrame): 包含股票数据的 DataFrame
        db_path (str): 目标数据库路径
        retention_days (int | None): 保留近 N 个自然日的记录。当为 None
            时（默认），从集中配置 ``Settings().market.retention_days``
            读取，该值由环境变量 ``DOGE_RETENTION_DAYS`` 控制，默认 730
            （必须 >= 730 以满足最宽分析视图 vw_market_breadth_cn 的 730 天
            窗口；低于该值会静默截断市场宽度扫描）。调用方可显式传入
            retention_days 以覆盖配置默认值。**该参数是破坏性的** —— 每次
            写入都会按 ticker 删除超过 N 天的旧行，且不可恢复。若 doge 配置
            包因运行环境问题无法导入，则回退为 730 并记录 WARNING，绝不
            回退到旧的 180 天默认值（那会重新引入静默截断 bug）。
    """
    from datetime import datetime, timedelta
    if retention_days is None:
        try:
            from doge.config import get_settings
            retention_days = get_settings().market.retention_days
        except Exception as e:
            retention_days = 730
            print(f"[WARN] could not load doge settings for retention_days, "
                  f"falling back to 730 (NOT 180): {e}")
    conn = get_db_connection(db_path)
    cutoff = (datetime.now() - timedelta(days=retention_days)).strftime('%Y-%m-%d')

    try:
        cur = conn.cursor()
        ticker = data['ticker'].iloc[0] if not data.empty else 'UNKNOWN'
        cur.execute(
            "SELECT MAX(date) FROM stock_prices WHERE ticker = ?", (ticker,)
        )
        max_existing = cur.fetchone()[0]

        if max_existing:
            new_data = data[data['date'] > max_existing]
            if new_data.empty:
                return
            new_data.to_sql('stock_prices', conn, if_exists='append', index=False)
        else:
            data.to_sql('stock_prices', conn, if_exists='append', index=False)

        # 删除该 ticker 的过期数据
        conn.execute(
            "DELETE FROM stock_prices WHERE ticker = ? AND date < ?",
            (ticker, cutoff)
        )
        conn.commit()
    except Exception as e:
        pass
    finally:
        conn.close()

def get_tickers_sync_state(db_path, tickers):
    """批量查询多只票在 DB 中的最新日期和条数，用于增量下载。

    Args:
        db_path (str): SQLite 数据库路径
        tickers (list[str]): 股票代码列表

    Returns:
        dict: {ticker: {"latest_date": str|None, "row_count": int}}
    """
    conn = get_db_connection(db_path)
    try:
        cur = conn.cursor()
        # SQLite 有参数个数限制 (999)，分批查询
        BATCH = 900
        result = {}
        for i in range(0, len(tickers), BATCH):
            batch = tickers[i:i + BATCH]
            placeholders = ','.join('?' * len(batch))
            sql = f"""
                SELECT ticker, MAX(date) AS latest_date, COUNT(*) AS row_count
                FROM stock_prices
                WHERE ticker IN ({placeholders})
                GROUP BY ticker
            """
            cur.execute(sql, batch)
            for row in cur.fetchall():
                result[row[0]] = {"latest_date": row[1], "row_count": row[2]}
        # 补全未查询到的 ticker
        for t in tickers:
            if t not in result:
                result[t] = {"latest_date": None, "row_count": 0}
        return result
    except Exception as e:
        print(f"[ERR] get_tickers_sync_state failed: {e}")
        return {t: {"latest_date": None, "row_count": 0} for t in tickers}
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
            print(f"[MIGRATE] altering table {table_name}: adding column {col_name}...")
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                print(f"[WARN] migration warning: {e}")

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
        print(f"[OK] macro report archived (Analyst: {analyst})")
    except Exception as e:
        print(f"[ERR] macro report archive failed: {e}")
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
        print(f"[OK] industry report archived (Analyst: {analyst})")
    except Exception as e:
        print(f"[ERR] report archive failed: {e}")
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
        print("[OK] AI insight saved to database")
    except Exception as e:
        print(f"[ERR] error saving AI insight: {e}")
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
        print(f"[ERR] error querying AI insights: {e}")
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
            print(f"[OK] entity '{name}' added to knowledge base")
        else:
            print(f"[WARN] entity '{name}' already exists, skipped")
    except Exception as e:
        print(f"[ERR] error adding entity: {e}")
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
        print(f"[OK] relation '{source} -> {relation} -> {target}' added to knowledge graph")
    except Exception as e:
        print(f"[ERR] error adding relation: {e}")
    finally:
        conn.close()

def initialize_system_dbs():
    """
    系统冷启动初始化：确保所有必要的数据库文件和表结构存在
    增强错误处理版本
    """
    import os
    
    try:
        # 1. 确定数据目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        data_dir = os.path.join(project_root, 'data')
        
        try:
            os.makedirs(data_dir, exist_ok=True)
            print(f"[INIT] checking database integrity ({data_dir})...")
        except PermissionError as e:
            print(f"[ERR] permission denied creating dir {data_dir}: {e}")
            return False
        except Exception as e:
            print(f"[ERR] failed to create data dir: {e}")
            return False

        # 2. 创建报告目录
        report_dirs = ['macro_report', 'micro_report', 'research_report']
        for dir_name in report_dirs:
            dir_path = os.path.join(project_root, dir_name)
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"   [DIR] ensured: {dir_name}")
            except Exception as e:
                print(f"   [WARN] failed to create dir {dir_name}: {e}")
                # 继续执行，不中断

        # 3. 初始化 A股/美股 数据库 (如果不存在)
        # 即使是空的，也先建立连接以生成文件
        for db_name in ['market_data_cn.db', 'market_data_us.db']:
            db_path = os.path.join(data_dir, db_name)
            if not os.path.exists(db_path):
                print(f"   [WARN] {db_name} not found, initializing...")
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    # 创建基础表结构 (stock_prices)
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS stock_prices (
                            ticker TEXT,
                            date TEXT,
                            open REAL, high REAL, low REAL, close REAL,
                            volume INTEGER, amount REAL,
                            PRIMARY KEY (ticker, date)
                        )
                    ''')
                    conn.commit()
                    conn.close()
                    print(f"   [OK] {db_name} created")
                except Exception as e:
                    print(f"   [ERR] failed to init {db_name}: {e}")
                    # 继续初始化其他数据库

        # 4. 初始化 研报智库 (包含自动迁移逻辑)
        # 调用现有的 save_research_report 逻辑来触发建表，或者直接建表
        research_db = os.path.join(data_dir, 'research_insights.db')
        try:
            conn = sqlite3.connect(research_db)
            cursor = conn.cursor()
            
            # 建表：Macro Reports
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS macro_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT, timestamp TEXT, tags TEXT, analyst TEXT,
                    risk_signal TEXT, volatility TEXT, content TEXT
                )
            ''')
            
            # 建表：Research Reports
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS research_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT, timestamp TEXT, tags TEXT, analyst TEXT,
                    title TEXT, content TEXT
                )
            ''')
            conn.commit()
            conn.close()
            print("   [OK] research database check complete")
        except Exception as e:
            print(f"   [ERR] research database init failed: {e}")
            # 继续执行

        print("[INIT] system databases ready")
        return True
        
    except Exception as e:
        print(f"[ERR] unknown error during system init: {e}")
        return False