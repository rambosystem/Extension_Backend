import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import Term, Embedding
from app.db.database import SessionLocal
from faiss_engine.vector_store import FAISSVectorStore
from faiss_engine.embeddings import BGE_M3EmbeddingService

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.vector_store = FAISSVectorStore()
        self.embedding_model = BGE_M3EmbeddingService()

    def get_db(self):
        """获取数据库会话"""
        db = SessionLocal()
        try:
            return db
        except Exception as e:
            db.close()
            raise e

    def update_embedding_status(self, status: str, db: Session = None):
        """更新embedding状态"""
        if db is None:
            db = self.get_db()

        try:
            embedding_record = db.query(Embedding).first()

            if not embedding_record:
                embedding_record = Embedding()
                db.add(embedding_record)

            embedding_record.embedding_status = status

            if status == "success":
                embedding_record.last_embedding_time = datetime.now()

            db.commit()
            db.refresh(embedding_record)

            logger.info(f"Updated embedding status to: {status}")

        except Exception as e:
            logger.error(f"Error updating embedding status: {e}")
            db.rollback()
            raise e
        finally:
            if db:
                db.close()

    def build_embeddings_for_user(self, user_id: int):
        """为用户构建embedding向量"""
        db = self.get_db()

        try:
            # 更新状态为构建中
            self.update_embedding_status("building", db)

            # 获取用户的所有术语
            terms = db.query(Term).filter(Term.user_id == user_id).all()

            if not terms:
                logger.info(f"No terms found for user {user_id}")
                self.update_embedding_status("success", db)
                return {"message": "No terms to process", "processed_count": 0}

            logger.info(f"Building embeddings for {len(terms)} terms")

            # 重建向量索引
            success = self.vector_store.rebuild_index([
                {
                    "term_id": term.term_id,
                    "en": term.en,
                    "cn": term.cn,
                    "jp": term.jp
                }
                for term in terms
            ])

            if success:
                # 保存向量索引
                self.vector_store.save()

                # 更新状态为成功
                self.update_embedding_status("success", db)

                logger.info(
                    f"Successfully built embeddings for {len(terms)} terms")
                return {
                    "message": "Embeddings built successfully",
                    "processed_count": len(terms)
                }
            else:
                # 更新状态为失败
                self.update_embedding_status("failed", db)

                logger.error("Failed to build embeddings")
                return {
                    "message": "Failed to build embeddings",
                    "processed_count": 0
                }

        except Exception as e:
            logger.error(f"Error building embeddings: {e}")
            self.update_embedding_status("failed", db)
            raise e
        finally:
            db.close()

    def build_embeddings_for_all_users(self):
        """为所有用户构建embedding向量"""
        db = self.get_db()

        try:
            # 更新状态为构建中
            self.update_embedding_status("building", db)

            # 获取所有术语
            terms = db.query(Term).all()

            if not terms:
                logger.info("No terms found")
                self.update_embedding_status("success", db)
                return {"message": "No terms to process", "processed_count": 0}

            logger.info(
                f"Building embeddings for {len(terms)} terms from all users")

            # 重建向量索引
            success = self.vector_store.rebuild_index([
                {
                    "term_id": term.term_id,
                    "en": term.en,
                    "cn": term.cn,
                    "jp": term.jp
                }
                for term in terms
            ])

            if success:
                # 保存向量索引
                self.vector_store.save()

                # 更新状态为成功
                self.update_embedding_status("success", db)

                logger.info(
                    f"Successfully built embeddings for {len(terms)} terms")
                return {
                    "message": "Embeddings built successfully",
                    "processed_count": len(terms)
                }
            else:
                # 更新状态为失败
                self.update_embedding_status("failed", db)

                logger.error("Failed to build embeddings")
                return {
                    "message": "Failed to build embeddings",
                    "processed_count": 0
                }

        except Exception as e:
            logger.error(f"Error building embeddings: {e}")
            self.update_embedding_status("failed", db)
            raise e
        finally:
            db.close()

    def search_similar_terms(self, query: str, top_k: int = 5, threshold: float = 0.7):
        """搜索相似术语"""
        try:
            results = self.vector_store.search_similar_terms(
                query, top_k, threshold)
            return results
        except Exception as e:
            logger.error(f"Error searching similar terms: {e}")
            raise e

    def get_embedding_stats(self):
        """获取embedding统计信息"""
        try:
            stats = self.vector_store.get_stats()
            return stats
        except Exception as e:
            logger.error(f"Error getting embedding stats: {e}")
            raise e
