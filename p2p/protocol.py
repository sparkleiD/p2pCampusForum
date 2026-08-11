"""
P2P 网络消息协议定义.

所有节点间通信统一使用此格式.
"""

from dataclasses import dataclass
from typing import Optional, List
import json


# ---------- 消息类型常量 ----------
class MsgType:
    # 审核相关
    AUDIT_REQUEST = "audit_request"       # 请求审核某条内容
    AUDIT_RESPONSE = "audit_response"     # 返回审核结果
    
    # 内容发布
    POST_PUBLISH = "post_publish"         # 新帖子发布
    COMMENT_PUBLISH = "comment_publish"   # 新评论发布
    
    # 同步相关
    SYNC_REQUEST = "sync_request"         # 请求全量数据
    SYNC_RESPONSE = "sync_response"       # 返回全量数据
    
    # 共识相关(分布式共识，暂不用)
    CONSENSUS_REQUEST = "consensus_request"   # 请求参与共识投票
    CONSENSUS_VOTE = "consensus_vote"         # 投票结果


@dataclass
class Message:
    """
    所有 P2P 消息的统一包装格式.
    
    字段说明:
        msg_id: 消息唯一ID (UUID)
        msg_type: 消息类型 (见 MsgType)
        sender: 发送节点的 PeerID
        timestamp: 消息时间戳 (ISO格式)
        payload: 消息体 (dict, 具体结构见各消息类型)
    """
    msg_id: str
    msg_type: str
    sender: str
    timestamp: str
    payload: dict

    def to_json(self) -> str:
        return json.dumps({
            "msg_id": self.msg_id,
            "msg_type": self.msg_type,
            "sender": self.sender,
            "timestamp": self.timestamp,
            "payload": self.payload
        })

    @classmethod
    def from_json(cls, data: str) -> "Message":
        obj = json.loads(data)
        return cls(
            msg_id=obj["msg_id"],
            msg_type=obj["msg_type"],
            sender=obj["sender"],
            timestamp=obj["timestamp"],
            payload=obj["payload"]
        )


# ---------- 各消息类型的 payload 结构 ----------

# 1. AUDIT_REQUEST - 请求审核内容
# payload = {
#     "content_id": "post_xxx 或 comment_xxx",
#     "content_type": "post" | "comment",
#     "content": "待审核的文本内容"
# }

# 2. AUDIT_RESPONSE - 返回审核结果
# payload = {
#     "content_id": "post_xxx 或 comment_xxx",
#     "verdict": "pass" | "flag" | "reject",
#     "reason": "判断理由",
#     "confidence": 95
# }

# 3. POST_PUBLISH - 新帖子发布
# payload = {
#     "post_id": "xxx",
#     "content": "帖子内容",
#     "nickname": "匿名",
#     "final_verdict": "approved" | "rejected",
#     "created_at": "2026-08-09T12:00:00",
#     "votes_summary": {"pass": 2, "flag": 0, "reject": 1}  # 共识投票统计
# }

# 4. COMMENT_PUBLISH - 新评论发布
# payload = {
#     "comment_id": "xxx",
#     "post_id": "xxx",
#     "content": "评论内容",
#     "nickname": "匿名",
#     "final_verdict": "approved" | "rejected",
#     "created_at": "2026-08-09T12:00:00"
# }

# 5. CONSENSUS_REQUEST - 请求参与共识
# payload = {
#     "content_id": "xxx",
#     "content_type": "post" | "comment",
#     "content": "文本内容"
# }

# 6. CONSENSUS_VOTE - 投票结果
# payload = {
#     "content_id": "xxx",
#     "verdict": "pass" | "flag" | "reject",
#     "reason": "判断理由",
#     "confidence": 95
# }

# 7. SYNC_REQUEST - 同步请求
# payload = {
#     "last_sync": "2026-08-09T10:00:00"  # 只同步此时间之后的数据
# }

# 8. SYNC_RESPONSE - 同步响应
# payload = {
#     "posts": [...],
#     "comments": [...],
#     "audit_logs": [...]
# }