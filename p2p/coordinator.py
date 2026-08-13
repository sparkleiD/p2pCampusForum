"""
投票管理器 - 只负责创建会话、收集投票、等待唤醒
不包含任何决策逻辑，最终结果由 consensus.engine 决定
"""
import trio
from typing import Dict, List, Optional
from ai.base import Verdict

class VoteSession:
    def __init__(self, content_id: str):
        self.content_id = content_id
        self.votes: List[dict] = []   # [{"sender": peer_id, "verdict": {'verdict': 'pass', 'reason': '调试用', 'confidence': 100}}]
        self.event = trio.Event()
        self.finished = False

# 全局会话池
_sessions: Dict[str, VoteSession] = {}

def create_session(content_id: str) -> None:
    """创建投票会话（由 posts.py 调用）"""
    _sessions[content_id] = VoteSession(content_id)

def process_vote(content_id: str, sender: str, verdict: Verdict) -> bool:
    """
    存入一张投票（由 handler.handle_audit_response 调用）
    返回: 是否成功处理
    """
    session = _sessions.get(content_id)
    if not session or session.finished:
        return False
    # 去重
    if any(v['sender'] == sender for v in session.votes):
        return False
    session.votes.append({'sender': sender, 'verdict': verdict})
    session.event.set()   # 唤醒等待者
    return True

async def wait_for_consensus(
    content_id: str,
    content: str,
    nickname: str,
    timeout_seconds: float,
    consensus_threshold: int
) -> Verdict:
    """
    等待投票收集完成（超时或达到最小票数），
    然后从 _sessions 中取出所有投票，调用 consensus.engine.decide() 决策
    """
    session = _sessions.get(content_id)
    if not session:
        raise ValueError(f"会话 {content_id} 不存在")
    
    try:
        # 1. 等待投票
        with trio.move_on_after(timeout_seconds):
            while not session.finished and len(session.votes) < consensus_threshold:
                await session.event.wait()
                session.event = trio.Event()   # 重置事件供下一票使用
        
        print(session.votes)
        # 2. 收集投票（只取 verdict 字符串列表）
        votes = [v['verdict'] for v in session.votes]
        
        # 3. 调用共识引擎决策（完全外部化）
        from consensus.engine import majority_vote
        final_verdict = majority_vote(votes, content, nickname)
        session.finished = True
        return final_verdict
        
    finally:
        # 4. 清理会话
        if content_id in _sessions:
            del _sessions[content_id]