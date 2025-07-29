#文件架构
EXTENSION_BACKEND [SSH...]/
├── app/                          # 主应用目录
│   ├── __init__.py              # 应用包初始化
│   ├── main.py                  # FastAPI应用入口
│   ├── config.py                # 配置文件
│   └── dependencies.py          # 依赖注入
│
├── api/                         # API路由目录
│   ├── __init__.py
│   ├── routes/                  # 路由模块
│   │   ├── __init__.py
│   │   ├── documents.py         # 文档相关API
│   │   ├── search.py            # 搜索相关API
│   │   └── admin.py             # 管理相关API
│   └── middleware.py            # 中间件
│
├── db/                          # 数据库相关
│   ├── __init__.py
│   ├── database.py              # 数据库连接
│   ├── models.py                # 数据库模型
│   └── migrations/              # 数据库迁移文件
│
├── faiss_engine/                # FAISS向量引擎
│   ├── __init__.py
│   ├── vector_store.py          # 向量存储管理
│   ├── embeddings.py            # 文本嵌入服务
│   └── search_engine.py         # 搜索引擎
│
├── models/                      # Pydantic模型
│   ├── __init__.py
│   ├── schemas.py               # API请求/响应模型
│   └── base.py                  # 基础模型
│
├── services/                    # 业务逻辑服务
│   ├── __init__.py
│   ├── document_service.py      # 文档处理服务
│   ├── search_service.py        # 搜索服务
│   └── index_service.py         # 索引管理服务
│
├── venv/                        # 虚拟环境
├── .env                         # 环境变量配置
├── .gitignore                   # Git忽略文件
├── requirements.txt             # 项目依赖
└── main.py                      # 项目启动入口