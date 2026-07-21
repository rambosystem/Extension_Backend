# Extension Backend API

浏览器扩展的后端服务，提供两块能力：**术语匹配**（翻译辅助）和 **Lokalise 集成**（翻译 key/tag 同步与检索）。

技术栈：FastAPI + SQLAlchemy + MySQL，gunicorn / UvicornWorker 多进程部署。

## 项目结构

```
extension_backend/
├── app/
│   ├── main.py                 # FastAPI 实例、CORS、注册 router、/ 与 /health
│   ├── config.py               # pydantic Settings（DB / API 配置）
│   ├── db/database.py          # SQLAlchemy engine / SessionLocal / get_db 依赖
│   ├── models/
│   │   ├── models.py           # ORM 表：User / Term / LokaliseKey / LokaliseTag
│   │   └── schemas.py          # Pydantic 请求 / 响应模型
│   └── api/router/
│       ├── user.py             # /users        用户术语 CRUD
│       ├── term_match.py       # /term-match   字符串术语匹配
│       └── lokalise.py         # /lokalise     Lokalise webhook / 检索 / 自动补全
├── term_matching/
│   ├── string_matcher.py       # StringTermMatcher（进程内，无模型 / 无 FAISS）
│   └── README.md
├── migrations/                 # 手写 SQL 迁移
├── gunicorn.conf.py            # 生产 gunicorn 配置
├── extension-backend.service   # systemd 服务单元
├── *_production.sh             # 启动 / 停止 / 重启 / 状态 / 监控脚本
├── requirements.txt
└── main.py                     # 本地开发启动入口（uvicorn app.main:app）
```

## 两大业务域

### ① 术语匹配（`/term-match`, `/users`）

用户维护术语表（en/cn/jp），扩展传入文本，后端实时从 DB 读取该用户术语，
用 [`StringTermMatcher`](term_matching/string_matcher.py) 做归一化整词匹配
（最长优先、不重叠、词边界保护），返回命中的 term_id。

无深度模型、无 FAISS 索引，纯进程内逻辑，单请求毫秒级。
详见 [term_matching/README.md](term_matching/README.md)。

### ② Lokalise 集成（`/lokalise`）

- `POST /lokalise/webhook`：接收 Lokalise 的 key 增 / 改 / 删事件
  （`project.key(s).added/modified/deleted`），同步落库到 `lokalise_keys` / `lokalise_tags`
- `GET /lokalise/keys/{project_id}`、`/keys/{project_id}/{key_id}`：列表 / 详情
- `POST /lokalise/search-by-names`：按 key_name 批量查询
- `GET /lokalise/autocomplete/keys`、`/autocomplete/tags`：扩展输入框自动补全

设计说明见 [LOKALISE_DESIGN.md](LOKALISE_DESIGN.md)、[TAG_TABLE_IMPLEMENTATION.md](TAG_TABLE_IMPLEMENTATION.md)。

## 数据库（MySQL `edge_extension_db`）

| 表 | 用途 |
|---|---|
| `users` | 用户 |
| `terms` | 用户术语（en/cn/jp） |
| `lokalise_keys` | Lokalise key + tags(JSON) |
| `lokalise_tags` | tag 独立维护（usage_count / last_used_at 排序） |

ORM 已声明索引，`Base.metadata.create_all()` 会在新库自动建表；
线上库补齐 / 变更见 `migrations/` 下的 SQL。

## 快速开始

### 环境要求
- Python 3.12
- MySQL 5.7+

### 安装与配置
```bash
pip install -r requirements.txt
```

`.env`（数据库连接）：
```env
DB_HOST=localhost
DB_PORT=2069
DB_USER=<user>
DB_PASSWORD=<password>
DB_NAME=edge_extension_db

API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
```

### 本地开发
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# 或
python main.py
```

### 生产部署
```bash
./start_production.sh      # 启动（gunicorn + systemd）
./status_production.sh     # 查看状态
./restart_production.sh    # 重启
./stop_production.sh       # 停止
```
详见 [PRODUCTION_SCRIPTS_README.md](PRODUCTION_SCRIPTS_README.md)。

## API 文档

服务启动后 FastAPI 自动提供交互式文档：

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`
- 健康检查: `/health`
