# storage/database.py
import sqlite3
import os

# 数据库文件路径(项目根目录下的 data 文件夹)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "posts.db")

def get_connection():
    """获取数据库连接"""
    # 确保 data 文件夹存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """初始化数据库：创建两张表"""
    conn = get_connection()
    cursor = conn.cursor()

    # 帖子表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            post_id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            nickname TEXT,
            status TEXT DEFAULT 'pending',
            final_verdict TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # AI审核日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT NOT NULL,
            comment_id TEXT,
            node_id TEXT,
            ai_model TEXT NOT NULL,
            verdict TEXT NOT NULL,
            reason TEXT,
            confidence INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(post_id)
        )
    """)

    #评论表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            comment_id TEXT PRIMARY KEY,
            post_id TEXT NOT NULL,
            content TEXT NOT NULL,
            nickname TEXT DEFAULT '匿名',
            status TEXT DEFAULT 'pending',
            final_verdict TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(post_id)
        )
    """)

    conn.commit()
    conn.close()
    print("数据库初始化完成")