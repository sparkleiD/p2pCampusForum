# web/routes/posts.py
"""
帖子相关 API 路由.
"""

import uuid
from dataclasses import asdict
from datetime import datetime
from fastapi import APIRouter, Form, HTTPException, Request

from storage import repositories as repo
from ai.factory import create_judge
from consensus.engine import majority_vote
from p2p.protocol import Message, MsgType
from config import PUBSUB_TOPIC
from web.websocket import broadcast_new_post

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.post("/")
async def create_post(
    request: Request,
    content: str = Form(...),
    nickname: str = Form("匿名")
):
    # ========== 第1步：AI审核（先审，通过后再保存） ==========
    try:
        judge = create_judge()
        local_result = judge.judge(content,nickname)
    except Exception as e:
        print(f"❌ AI 审核失败: {e}")
        raise HTTPException(
            status_code=503,
            detail="AI 审核服务暂时不可用，请稍后重试"
        )

    # ========== 第2步：如果本地AI判定为reject，直接拒绝，不保存 ==========
    if local_result.verdict == "reject":
        return {
            "status": "rejected",
            "message": f"AI 审核未通过：{local_result.reason}",
            "verdict": local_result.verdict,
            "reason": local_result.reason
        }

    # ========== 第3步：只有 pass 或 flag 才继续 ==========
    post_id = str(uuid.uuid4())

    # 保存帖子
    repo.save_post(post_id, content, nickname)

    # 保存本地审核日志
    repo.save_audit_log(
        post_id=post_id,
        node_id="local",
        ai_model="local",
        verdict=local_result.verdict,
        reason=local_result.reason,
        confidence=local_result.confidence
    )

    # ========== 第4步：广播审核请求给其他节点 ==========
    pubsub = request.app.state.pubsub
    peer_id = request.app.state.peer_id

    if pubsub and peer_id:
        msg = Message(
            msg_id=str(uuid.uuid4()),
            msg_type=MsgType.AUDIT_REQUEST,
            sender=peer_id,
            timestamp=datetime.now().isoformat(),
            payload={
                "post_id": post_id,
                "content": content,
                "nickname": nickname
            }
        )
        await pubsub.publish(asdict(msg))
        print(f"📤 已广播审核请求: {post_id}")
    else:
        print(f"⚠️ P2P 未启用，仅使用本地审核: {post_id}")

    # ========== 第5步：收集审核结果并共识 ==========
    verdicts = [local_result]
    consensus_result = majority_vote(verdicts)
    final_verdict = consensus_result["final_verdict"]

    # ========== 第6步：更新帖子状态 ==========
    repo.update_post_status(post_id, final_verdict, final_verdict)

    # ========== 第7步：WebSocket推送 ==========
    if final_verdict == "approved":
        await broadcast_new_post({
            "post_id": post_id,
            "content": content,
            "nickname": nickname,
            "final_verdict": final_verdict,
            "created_at": datetime.now().isoformat()
        })
        print(f"📡 WebSocket 已推送新帖子: {post_id}")

    return {
        "post_id": post_id,
        "status": final_verdict,
        "votes": consensus_result["votes"],
        "details": consensus_result["details"],
        "message": "帖子发布成功" if final_verdict == "approved" else "帖子未通过审核"
    }


@router.get("/")
async def list_posts(limit: int = 100):
    rows = repo.get_all_posts(limit)
    posts = []
    for row in rows:
        posts.append({
            "post_id": row[0],
            "content": row[1],
            "nickname": row[2],
            "status": row[3],
            "final_verdict": row[4],
            "created_at": row[5]
        })
    return {"posts": posts, "count": len(posts)}


@router.get("/{post_id}")
async def get_post(post_id: str):
    post = repo.get_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    logs = repo.get_audit_logs(post_id=post_id)
    return {
        "post": {
            "post_id": post[0],
            "content": post[1],
            "nickname": post[2],
            "status": post[3],
            "final_verdict": post[4],
            "created_at": post[5]
        },
        "audit_logs": [
            {
                "ai_model": log[0],
                "verdict": log[1],
                "reason": log[2],
                "confidence": log[3],
                "created_at": log[4]
            }
            for log in logs
        ]
    }