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
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "Extension"

    # BGE-M3 Embedding配置 - 离线模式
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_MAX_LENGTH: int = 512

    # 离线模型配置
    TRANSFORMERS_OFFLINE: bool = True
    HF_HUB_OFFLINE: bool = True
    HF_ENDPOINT: str = "https://hf-mirror.com"
    MODEL_CACHE_DIR: str = "./model_cache"

    # FAISS向量持久化配置
    FAISS_INDEX_PATH: str = "./faiss_indexes"
    FAISS_INDEX_TYPE: str = "IndexFlatIP"
    VECTOR_PERSISTENCE_ENABLED: bool = True
    AUTO_SAVE_INTERVAL: int = 100  # 每100次操作自动保存

    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"


settings = Settings()
