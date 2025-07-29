from fastapi import FastAPI
from app.api.config import settings
from app.db.database import engine
from sqlalchemy import text
from app.api.router import user
from fastapi.middleware.cors import CORSMiddleware

# 创建FastAPI应用实例
app = FastAPI(
    title="FAISS Vector Search API",
    description="基于FAISS的向量搜索API",
    version="1.0.0",
    debug=settings.DEBUG
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(user.router)

# 根路径


@app.get("/")
async def root():
    return {
        "message": "FAISS Vector Search API is running!",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.get("/test-db")
async def test_database():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 as test_value"))
            row = result.fetchone()
            return {
                "status": "Database connection successful",
                "test_result": row[0] if row else None,
                "database_url": f"mysql://{connection.engine.url.host}:{connection.engine.url.port}/{connection.engine.url.database}"
            }
    except Exception as e:
        return {
            "status": "Database connection failed",
            "error": str(e),
            "error_type": type(e).__name__
        }

# 健康检查端点


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",  # 后续会实现真实的数据库检查
        "faiss_engine": "ready"   # 后续会实现真实的FAISS检查
    }
