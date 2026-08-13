# 去中心化校园论坛p2pCampusForum

p2pCampusForum/
│
├── main.py                          # 程序入口，启动 P2P + Web 服务器
├── config.py                        # 配置文件（API密钥、端口、话题等）
├── requirements.txt                 # Python 依赖清单
├── .env                             # 环境变量（API_KEY 等，不提交 Git）
├── test_ai.py                       # AI 配置测试工具
├── test_prompt.py                   # 提示词测试工具
│
├── ai/                              # AI 审核模块
│   ├── __init__.py
│   ├── base.py                      # Verdict 数据类 + BaseJudge 基类
│   ├── factory.py                   # 根据 AI_MODE 创建审核器
│   ├── api/                         # 云端 API 审核器
│   │   ├── __init__.py
│   │   └── openai_compat_judge.py   # OpenAI 兼容格式审核器（通义千问等）
│   └── local/                       # 本地模型审核器
│       ├── __init__.py
│       └── ollama_judge.py          # Ollama 本地模型审核器
│
├── p2p/                             # P2P 网络模块
│   ├── __init__.py
│   ├── network.py                   # libp2p Host 创建与管理
│   ├── discovery.py                 # mDNS 服务注册（含固定域名抢占）
│   ├── protocol.py                  # 消息格式定义（Message + MsgType）
│   ├── pubsub.py                    # PubSub 发布订阅（GossipSub）
│   ├── router.py                    # P2P 消息处理路由
│   └── handler.py                   # P2P 消息处理回调函数集合
│
├── storage/                         # 数据存储模块
│   ├── __init__.py
│   ├── database.py                  # SQLite 连接 + 建表（posts/audit_log/comments）
│   └── repositories.py              # CRUD 操作（帖子/评论/审核日志）
│
├── consensus/                       # 共识引擎模块
│   ├── __init__.py
│   └── engine.py                    # 多数投票共识（majority_vote）
│
├── web/                             # Web 服务层
│   ├── __init__.py
│   ├── server.py                    # FastAPI 主应用（挂载路由 + 静态文件）
│   ├── websocket.py                 # WebSocket 连接管理 + 广播函数
│   └── routes/                      # API 路由
│       ├── __init__.py
│       ├── posts.py                 # 帖子 API（发帖/查帖/详情）
│       ├── comments.py              # 评论 API（发评论/查评论）
│       └── sync.py                  # 数据同步 API（新节点拉取历史数据）
│
├── frontend/                        # 前端静态文件
│   ├── index.html                   # 主页面
│   ├── css/
│   │   └── style.css                # 样式（含响应式设计）
│   └── js/
│       ├── app.js                   # 前端主逻辑（发帖/列表/详情弹窗）
│       └── websocket.js             # WebSocket 客户端（自动连接 + 重连）
│
├── utils/                           # 工具模块
│   ├── __init__.py
│   └── logger.py                    # 日志配置
│
├── data/                            # 运行时数据（不提交 Git）
│   └── posts.db                     #  SQLite 数据库文件
│
└── venv/                            # Python 虚拟环境（不提交 Git）
