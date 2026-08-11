import os
from dotenv import load_dotenv

load_dotenv()

# 服务端口
WEB_PORT = 9099
P2P_PORT = 9001

# AI模式配置
AI_MODE = "api" # 可选值: "api" 或 "local"
# 支持所有 OpenAI 兼容格式的 API
# 切换服务商只需修改 base_url 和 model_name
API_BASE_URL = os.getenv("AI_API_BASE_URL",default="https://api.openai.com/v1")
API_MODEL_NAME = "qwen3.7-plus"
API_KEY = os.getenv("AI_API_KEY",default="unknown")

OLLAMA_HOST = "http://localhost:11434" # Ollama 服务地址（默认本地）
OLLAMA_MODEL = "qwen2.5:7b" # 本地模型名（如果使用本地模式）

AI_TIMEOUT = 30 #秒

# mDNS服务名(便于手机发现)
MDNS_SERVICE_NAME = "campusforum"
MDNS_SERVICE_TYPE = "_http._tcp.local."
# P2P服务名(便于节点发现)
P2P_SERVICE_TYPE = "_p2p._tcp.local."

# PubSub话题(节点之间通过这个话题广播新帖子)
PUBSUB_TOPIC = "/campusforum/posts"

# 共识配置
CONSENSUS_RETRY_COUNT = 1  # 分歧时最多重审次数
CONSENSUS_FLAG_THRESHOLD = 2  # 多少票存疑视为存疑