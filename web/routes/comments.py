# web/routes/comments.py
"""
评论相关 API 路由.

提供发评论、查评论等接口.
"""

import uuid
from fastapi import APIRouter, Form, HTTPException

from storage import repositories as repo
from ai.factory import create_judge
from consensus.engine import majority_vote

router = APIRouter(prefix="/api/comments", tags=["comments"])


@router.post("/")
async def create_comment(
    post_id: str = Form(...),
    content: str = Form(...),
    nickname: str = Form("匿名")
):
    """
    发布评论.

    流程：
    1. 检查帖子是否存在
    2. 保存评论到数据库（状态: pending）
    3. 调用本地 AI 审核
    4. 执行共识投票
    5. 更新评论状态
    """
    # 1. 检查帖子是否存在
    post = repo.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    # 2. 生成评论 ID
    comment_id = str(uuid.uuid4())[:8]

    # 3. 保存到数据库
    repo.save_comment(comment_id, post_id, content, nickname)

    # 4. 调用本地 AI 审核
    judge = create_judge()
    local_result = judge.judge(content,nickname)

    # 5. 保存审核日志
    repo.save_audit_log(
        post_id=post_id,
        comment_id=comment_id,
        node_id="local",
        ai_model="local",
        verdict=local_result.verdict,
        reason=local_result.reason,
        confidence=local_result.confidence
    )

    # 6. 共识投票（当前仅本地）
    verdicts = [local_result]
    consensus_result = majority_vote(verdicts)
    final_verdict = consensus_result["final_verdict"]

    # 7. 更新评论状态
    repo.update_comment_status(comment_id, final_verdict, final_verdict)

    return {
        "comment_id": comment_id,
        "post_id": post_id,
        "status": final_verdict,
        "votes": consensus_result["votes"],
        "details": consensus_result["details"],
        "message": "评论发布成功" if final_verdict == "approved" else "评论未通过审核"
    }


@router.get("/{post_id}")
async def get_comments(post_id: str, limit: int = 50):
    """
    获取某条帖子的所有评论.
    """
    post = repo.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    rows = repo.get_comments_by_post(post_id, limit)

    comments = []
    for row in rows:
        comments.append({
            "comment_id": row[0],
            "content": row[1],
            "nickname": row[2],
            "status": row[3],
            "final_verdict": row[4],
            "created_at": row[5]
        })

    return {"post_id": post_id, "comments": comments, "count": len(comments)}