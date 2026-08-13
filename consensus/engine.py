"""
共识引擎 - 基于评分平均的简单实现

每个投票映射为分数：
    - "pass"   -> 1.0
    - "flag"   -> 0.5  (存疑)
    - "reject" -> 0.0

最终结果根据平均分判定：
    - >= 0.6  -> "pass"
    - <= 0.4  -> "reject"
    - 否则    -> "flag" (存疑)

如果票数不足，降级使用本地 AI 作为兜底。
"""

from typing import List, Optional
from config import CONSENSUS_THRESHOLD
from ai.base import Verdict

# ---------- 评分映射 ----------
SCORE_MAP = {
    "pass": 1.0,
    "flag": 0.5,
    "reject": 0.0
}

# 判定阈值
PASS_THRESHOLD = 0.5

def map_verdict_to_score(verdict: str) -> float:
    """将 verdict 字符串转为分数"""
    return SCORE_MAP.get(verdict, 0.0)  # 未知类型按 0 处理

def map_score_to_verdict(score: float) -> str:
    """将平均分映射回 verdict"""
    if score > PASS_THRESHOLD:
        return Verdict("pass", "not supported yet", 100)
    else:
        return Verdict("reject", "not supported yet", 100)

def majority_vote(
    votes: List[Verdict],
    content: str,
    nickname: str,
    fallback_to_local: bool = False
) -> Verdict:
    """
    最终决策函数

    Args:
        votes: 所有收到的投票 verdict 对象列表
        content: 原文内容（用于兜底时调用本地 AI）
        nickname: 作者昵称（用于兜底）
        min_votes: 有效投票最少数量，低于此值视为票数不足
        fallback_to_local: 票数不足时是否降级到本地 AI

    Returns:
        最终 verdict 字符串 ("pass" / "reject")
    """
    # 如果票数足够，走评分平均
    if len(votes) >= CONSENSUS_THRESHOLD:
        print("[engine] 票数足够，进行评分平均")
        scores = [map_verdict_to_score(v['verdict']) for v in votes]
        avg_score = sum(scores) / len(scores)
        final_verdict = map_score_to_verdict(avg_score)
        # 可以在这里记录 reason，但暂时不用，留空
        return final_verdict

    # 票数不足时的兜底策略
    if not fallback_to_local:
        # 不降级，直接返回 reject（保守）
        return "reject"

    if len(votes) == 0:
        # 没有任何投票，调用本地 AI
        print("[engine] 没有任何投票，调用本地 AI")
        from ai.factory import create_judge
        judge = create_judge()
        result = judge.judge(content, nickname)
        return result
    else:
        # 有少数票（但 < min_votes），仍然用平均分决定（即使样本不足）
        # 但为了保守，可以降低信任度，这里直接复用平均逻辑
        print("[engine] 有少数票，仍然用平均分决定")
        scores = [map_verdict_to_score(v['verdict']) for v in votes]
        avg_score = sum(scores) / len(scores)
        return map_score_to_verdict(avg_score)