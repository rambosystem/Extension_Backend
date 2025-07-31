from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, Boolean, ForeignKey, text, BigInteger, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True,
                     autoincrement=True, comment="用户唯一标识")
    username = Column(String(50), nullable=False,
                      unique=True, comment="用户名（唯一）")
    email = Column(String(100), nullable=False,
                   unique=True, comment="用户邮箱（唯一）")
    password_hash = Column(String(255), comment="密码哈希值")
    status = Column(String(20), default="active", comment="用户状态")
    created_at = Column(TIMESTAMP, server_default=text(
        "CURRENT_TIMESTAMP"), comment="账户创建时间")
    updated_at = Column(TIMESTAMP, server_default=text(
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment="最后更新时间")
    deleted_at = Column(TIMESTAMP, nullable=True, comment="软删除时间")

    # 关系映射
    terms = relationship("Term", back_populates="user")
    embeddings = relationship("Embedding", back_populates="user")


class Term(Base):
    __tablename__ = "terms"

    term_id = Column(Integer, primary_key=True,
                     autoincrement=True, comment="术语唯一标识")
    user_id = Column(Integer, ForeignKey(
        "users.user_id", ondelete="CASCADE"), nullable=False, comment="关联用户的外键")
    en = Column(String(255), nullable=False, comment="英文术语")
    cn = Column(String(255), comment="中文翻译")
    jp = Column(String(255), comment="日文翻译")
    created_at = Column(TIMESTAMP, server_default=text(
        "CURRENT_TIMESTAMP"), comment="术语创建时间")
    updated_at = Column(TIMESTAMP, server_default=text(
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment="最后更新时间")
    deleted_at = Column(TIMESTAMP, nullable=True, comment="软删除时间")

    # 关系映射
    user = relationship("User", back_populates="terms")


class Embedding(Base):
    __tablename__ = "embedding"

    id = Column(BigInteger, primary_key=True,
                autoincrement=True, comment="主键ID")
    user_id = Column(Integer, ForeignKey(
        "users.user_id", ondelete="CASCADE"), nullable=False, comment="关联用户的外键")
    embedding_status = Column(String(20), nullable=False,
                              default="pending", comment="embedding状态：building-构建中, completed-成功, failed-失败")
    last_embedding_time = Column(DateTime, nullable=True,
                                 comment="最后成功构建embedding的时间")

    # 关系映射
    user = relationship("User", back_populates="embeddings")
