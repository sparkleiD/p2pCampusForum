# consensus/engine.py
from collections import Counter
from config import CONSENSUS_RETRY_COUNT, CONSENSUS_FLAG_THRESHOLD


def majority_vote(verdicts, retry_count=0):
    """
    执行共识投票.
    
    返回:
        {
            "final_verdict": "approved" | "rejected" | "retry",
            "votes": {"pass": 1, "flag": 1, "reject": 1},
            "details": [...]
        }
    """
    if not verdicts:
        return {"final_verdict": "rejected", "votes": {}, "details": []}

    verdict_list = [v.verdict for v in verdicts]
    counter = Counter(verdict_list)

    pass_count = counter.get("pass", 0)
    flag_count = counter.get("flag", 0)
    reject_count = counter.get("reject", 0)

    # 规则1: 存疑票 >= 阈值 → 返回 flag（等待人工或自动降级）
    if flag_count >= CONSENSUS_FLAG_THRESHOLD:
        return {
            "final_verdict": "flag",
            "votes": dict(counter),
            "details": [{"verdict": v.verdict, "reason": v.reason, "confidence": v.confidence} for v in verdicts]
        }

    # 规则2: pass >= 2 且 reject < 2 → 通过
    if pass_count >= 2 and reject_count < 2:
        return {
            "final_verdict": "approved",
            "votes": dict(counter),
            "details": [{"verdict": v.verdict, "reason": v.reason, "confidence": v.confidence} for v in verdicts]
        }

    # 规则3: reject >= 2 → 拒绝
    if reject_count >= 2:
        return {
            "final_verdict": "rejected",
            "votes": dict(counter),
            "details": [{"verdict": v.verdict, "reason": v.reason, "confidence": v.confidence} for v in verdicts]
        }

    # 规则4: 分歧 → 需要重审
    if retry_count < CONSENSUS_RETRY_COUNT:
        return {
            "final_verdict": "retry",
            "votes": dict(counter),
            "details": [{"verdict": v.verdict, "reason": v.reason, "confidence": v.confidence} for v in verdicts]
        }

    # 重审次数用尽，默认拒绝（安全策略）
    return {
        "final_verdict": "rejected",
        "votes": dict(counter),
        "details": [{"verdict": v.verdict, "reason": v.reason, "confidence": v.confidence} for v in verdicts]
    }