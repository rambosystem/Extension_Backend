import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # API配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    # MySQL数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 2069
    DB_USER: str = "rambo"
    DB_PASSWORD: str = "Wx19971009."
    DB_NAME: str = "edge_extension_db"

    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        # 忽略 .env 中的遗留/无关变量（如已废弃的 EMBEDDING_* / FAISS_* 配置），
        # 避免部署环境残留旧键导致启动校验失败
        extra = "ignore"


settings = Settings()
