# storage/repositories.py
from .database import get_connection


# ============ 帖子操作 ============

def save_post(post_id, content, nickname="匿名"):
    """保存新帖子"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO posts (post_id, content, nickname, status) VALUES (?, ?, ?, 'pending')",
        (post_id, content, nickname)
    )
    conn.commit()
    conn.close()


def update_post_status(post_id, status, final_verdict=None):
    """更新帖子状态"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE posts SET status = ?, final_verdict = ? WHERE post_id = ?",
        (status, final_verdict, post_id)
    )
    conn.commit()
    conn.close()


def get_all_posts(limit=100):
    """获取最新帖子列表"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT post_id, content, nickname, status, final_verdict, created_at FROM posts WHERE status = 'pass' ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_post_by_id(post_id):
    """按ID查询单条帖子"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT post_id, content, nickname, status, final_verdict, created_at FROM posts WHERE post_id = ?",
        (post_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row and row[3] != "pass":
        return None
    return row


# ============ 评论操作 ============

def save_comment(comment_id, post_id, content, nickname="匿名"):
    """保存新评论"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO comments (comment_id, post_id, content, nickname, status) VALUES (?, ?, ?, ?, 'pending')",
        (comment_id, post_id, content, nickname)
    )
    conn.commit()
    conn.close()


def update_comment_status(comment_id, status, final_verdict=None):
    """更新评论状态"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE comments SET status = ?, final_verdict = ? WHERE comment_id = ?",
        (status, final_verdict, comment_id)
    )
    conn.commit()
    conn.close()


def get_comments_by_post(post_id, limit=50):
    """获取某条帖子的所有评论"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT comment_id, content, nickname, status, final_verdict, created_at FROM comments WHERE post_id = ? ORDER BY created_at ASC LIMIT ?",
        (post_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


# ============ 审核日志操作 ============

def save_audit_log(post_id, node_id, ai_model, verdict, reason, confidence, comment_id=None):
    """保存AI审核记录（同时支持帖子和评论）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_log (post_id, comment_id, node_id, ai_model, verdict, reason, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (post_id, comment_id, node_id, ai_model, verdict, reason, confidence)
    )
    conn.commit()
    conn.close()


def get_audit_logs(post_id=None, comment_id=None):
    """查询审核记录"""
    conn = get_connection()
    cursor = conn.cursor()
    if post_id:
        cursor.execute(
            "SELECT ai_model, verdict, reason, confidence, created_at FROM audit_log WHERE post_id = ?",
            (post_id,)
        )
    elif comment_id:
        cursor.execute(
            "SELECT ai_model, verdict, reason, confidence, created_at FROM audit_log WHERE comment_id = ?",
            (comment_id,)
        )
    else:
        cursor.execute("SELECT ai_model, verdict, reason, confidence, created_at FROM audit_log")
    rows = cursor.fetchall()
    conn.close()
    return rows


# ============ 数据同步 ============

def get_all_data_for_sync():
    """导出全量数据（供新节点同步用）"""
    conn = get_connection()
    cursor = conn.cursor()
    posts = cursor.execute("SELECT * FROM posts").fetchall()
    comments = cursor.execute("SELECT * FROM comments").fetchall()
    logs = cursor.execute("SELECT * FROM audit_log").fetchall()
    conn.close()
    return {"posts": posts, "comments": comments, "audit_logs": logs}