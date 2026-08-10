# ai/api/openai_compat_judge.py
import json
from openai import OpenAI
from ..base import BaseJudge, Verdict
from config import API_KEY, API_BASE_URL, API_MODEL_NAME, AI_TIMEOUT

# ========== 修改点 1: 提示词中限制 reason 字数 ==========
PROMPT = """你是一位校园论坛内容审核员, 请判断以下内容以及昵称是否违规.

违规标准（命中任意一条即违规）：
1. 辱骂或人身攻击.
2. 未经证实的谣言.
3. 广告或商业推广.
4. 他人隐私信息（手机号, 身份证号等）.
5. 色情或低俗内容.

【严格要求】请只输出纯 JSON, 不要包含任何其他文字或解释.
JSON 格式: {{"verdict": "pass/flag/reject", "reason": "简短理由(限10字内)", "confidence": 0-100}}

帖子内容：{content}, 昵称：{nickname}"""
# ========================================================


class OpenAICompatJudge(BaseJudge):
    """
    OpenAI 兼容格式的统一 API 审核器.
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL
        )
        self.model = API_MODEL_NAME

    def judge(self, content: str, nickname: str) -> Verdict:
        #调试用↓
        return Verdict(verdict="pass", reason="调试用", confidence=100)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": PROMPT.format(content=content, nickname=nickname)}],
            max_tokens=100,
            timeout=AI_TIMEOUT,
            temperature=0.1
        )

        # 打印 Token 消耗
        usage = response.usage
        print("=" * 45)
        print(f"📊 Token: 输入 {usage.prompt_tokens} / 输出 {usage.completion_tokens} / 总计 {usage.total_tokens}")
        print("=" * 45)

        raw = response.choices[0].message.content
        result = json.loads(raw)
        print(f"📝 审核结果: {result}")

        return Verdict(
            verdict=result["verdict"],
            reason=result["reason"],
            confidence=result["confidence"]
        )