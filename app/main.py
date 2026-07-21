from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.router import user
from app.api.router import term_match
from app.api.router import lokalise

# 创建FastAPI应用实例
app = FastAPI(
    title="Extension Backend API",
    description="术语匹配 / Lokalise Key 管理后端 API",
    version="1.0.0",
    debug=settings.DEBUG
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(user.router)
app.include_router(term_match.router)
app.include_router(lokalise.router)

# 根路径


@app.get("/")
async def root():
    return {
        "message": "Extension Backend API is running!",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

# 健康检查端点


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected"
    }
