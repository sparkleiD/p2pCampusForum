import json
import uuid
from dataclasses import asdict
from fastapi import HTTPException
from datetime import datetime
from ai.factory import create_judge
from .protocol import Message, MsgType
from storage import repositories as repo
from .coordinator import process_vote


async def handle_audit_request(data: dict, sender: str, pubsub):
    data_payload = data.get('payload', {})
    print(f"[PUBSUB] 📩 审核请求来自 {sender}: {data_payload.get('content', '')[:50]}...")

    try:
        judge = create_judge()
        response_result = judge.judge(data_payload.get('content'), data_payload.get('nickname'))
        print(response_result)
    except Exception as e:
        print(f"[PUBSUB] ❌ AI 审核失败: {e}")
        raise HTTPException(
            status_code=503,
            detail="AI 审核服务暂时不可用，请稍后重试"
        )

    my_peer_id = pubsub.host.get_id().pretty()
    if pubsub and my_peer_id:
        msg = Message(
            msg_id=str(uuid.uuid4()),
            msg_type=MsgType.AUDIT_RESPONSE,
            sender=my_peer_id,
            timestamp=datetime.now().isoformat(),
            payload={
                "content_id": data_payload.get('content_id'),
                "verdict": response_result,
            }
        )
        await pubsub.publish(asdict(msg))

async def handle_audit_response(data: dict, sender: str, pubsub):
    payload = data.get('payload', {})
    content_id = payload.get('content_id')
    verdict = payload.get('verdict') # Verdict 类型
    if content_id and verdict:
        # 只是存入投票，不涉及任何决策
        process_vote(content_id, sender, verdict)

async def handle_post_publish(data: dict, sender: str, pubsub):
    print(f"[PUBSUB] 📩 新帖子来自 {sender}: {data.get('payload', {}).get('post_id')}")
    # TODO: 保存到本地数据库，触发 WebSocket 推送

async def handle_comment_publish(data: dict, sender: str, pubsub):
    print(f"[PUBSUB] 📩 新评论来自 {sender}: {data.get('payload', {}).get('comment_id')}")
    # TODO: 保存到本地数据库

async def handle_sync_request(data: dict, sender: str, pubsub):
    print(f"[PUBSUB] 📩 同步请求来自 {sender}")
    # TODO: 响应全量数据

async def handle_sync_response(data: dict, sender: str, pubsub):
    print(f"[PUBSUB] 📩 同步响应来自 {sender}")
    # TODO: 将接收到的数据保存到本地数据库

async def handle_consensus_request(data: dict, sender: str, pubsub):
    print(f"[PUBSUB] 📩 共识请求来自 {sender}: {data.get('payload', {}).get('content_id')}")
    # TODO: 参与共识投票

async def handle_consensus_vote(data: dict, sender: str, pubsub):
    print(f"[PUBSUB] 📩 共识投票来自 {sender}: {data.get('payload', {}).get('verdict')}")
    # TODO: 收集投票
