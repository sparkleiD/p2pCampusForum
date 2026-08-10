from dataclasses import dataclass

@dataclass
class Verdict:
    verdict: str       # "pass" / "flag" / "reject"
    reason: str        # 判断理由
    confidence: int    # 置信度 0-100


class BaseJudge:
    """所有审核器的统一基类"""
    def judge(self, content: str, nickname: str) -> Verdict:
        raise NotImplementedError("子类必须实现 judge 方法")