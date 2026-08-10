# ai/local/ollama_judge.py
import json
import requests
from ..base import BaseJudge, Verdict
from config import OLLAMA_HOST, OLLAMA_MODEL, AI_TIMEOUT

# 审核提示词
PROMPT = """你是一位校园论坛内容审核员，请判断以下帖子是否违规.

违规标准（命中任意一条即违规）：
1. 辱骂或人身攻击.
2. 未经证实的谣言.
3. 广告或商业推广.
4. 他人隐私信息（手机号, 身份证号等）.
5. 色情或低俗内容.

输出JSON格式:{"verdict": "pass/flag/reject", "reason": "理由", "confidence": 0-100}

帖子内容：{content}"""


class OllamaJudge(BaseJudge):
    """
    本地 Ollama 审核器.

    通过 Ollama 的 HTTP API 调用本地模型, 完全离线运行.
    前置条件：安装 Ollama 并下载模型, 如 `ollama pull qwen2.5:7b`.

    扩展：如需更换模型, 修改 config.py 中的 OLLAMA_MODEL 即可.
    """

    def __init__(self, model_name: str = None):
        self.model = model_name or OLLAMA_MODEL
        self.host = OLLAMA_HOST

    def judge(self, content: str) -> Verdict:
        response = requests.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": PROMPT.format(content=content),
                "stream": False
            },
            timeout=AI_TIMEOUT
        )
        response.raise_for_status()
        result = json.loads(response.json()["response"])
        return Verdict(
            verdict=result["verdict"],
            reason=result["reason"],
            confidence=result["confidence"]
        )