from typing import List
from .base import BaseJudge
from config import AI_MODE


def create_judge() -> BaseJudge:
    """
    根据 AI_MODE 配置创建对应的审核器.

    当前支持的模式：
    - "api"  : 使用 OpenAI 兼容格式的云端 API
    - "local": 使用本地 Ollama

    扩展方法：
    1. 在 config.py 中新增模式常量（如 AI_MODE = "new_model").
    2. 在此函数中添加对应的 elif 分支.
    3. 在 ai/ 下新建对应的审核器类.
    """
    if AI_MODE == "api":
        from .api.openai_compat_judge import OpenAICompatJudge
        return OpenAICompatJudge()

    elif AI_MODE == "local":
        from .local.ollama_judge import OllamaJudge
        return OllamaJudge()

    else:
        raise ValueError(f"不支持的 AI_MODE: {AI_MODE}, 请选择 'api' 或 'local'")