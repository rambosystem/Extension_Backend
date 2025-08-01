import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import Term, Embedding
from app.db.database import SessionLocal
# 移除FAISSVectorStore导入，统一使用TermMatcher
from faiss_engine.embeddings import BGE_EmbeddingService

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        # 统一使用TermMatcher作为embedding引擎
        pass
        self.embedding_model = BGE_EmbeddingService()

    def get_db(self):
        """获取数据库会话"""
        db = SessionLocal()
        try:
            return db
        except Exception as e:
            db.close()
            raise e

    def update_embedding_status(self, status: str, user_id: int = None, db: Session = None):
        """更新embedding状态"""
        if db is None:
            db = self.get_db()

        try:
            if user_id:
                # 用户级别的状态管理
                embedding_record = db.query(Embedding).filter(
                    Embedding.user_id == user_id).first()

                if not embedding_record:
                    embedding_record = Embedding(user_id=user_id)
                    db.add(embedding_record)
            else:
                # 全局状态管理（兼容旧版本）
                embedding_record = db.query(Embedding).first()

                if not embedding_record:
                    embedding_record = Embedding()
                    db.add(embedding_record)

            embedding_record.embedding_status = status

            if status == "completed":
                embedding_record.last_embedding_time = datetime.now()

            db.commit()
            db.refresh(embedding_record)

            logger.info(
                f"Updated embedding status to: {status} for user: {user_id}")

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
            self.update_embedding_status("building", user_id, db)

            # 获取用户的所有术语
            terms = db.query(Term).filter(Term.user_id == user_id).all()

            if not terms:
                logger.info(f"No terms found for user {user_id}")
                self.update_embedding_status("completed", user_id, db)
                return {"message": "No terms to process", "processed_count": 0}

            logger.info(
                f"Building embeddings for {len(terms)} terms for user {user_id}")

            # 使用TermMatcher来重建索引，确保使用相同的embedding方法
            from term_matching.term_matcher import TermMatcher

            # 准备术语数据（只使用英文，与match时保持一致）
            terms_data = [
                {
                    "term_id": term.term_id,
                    "en": term.en
                }
                for term in terms
            ]

            try:
                # 使用TermMatcher重建索引
                matcher = TermMatcher()
                matcher.build_index_from_terms(terms_data)

                # 更新状态为成功
                self.update_embedding_status("completed", user_id, db)

                logger.info(
                    f"Successfully built embeddings for {len(terms)} terms for user {user_id}")
                return {
                    "message": "Embeddings built successfully",
                    "processed_count": len(terms),
                    "user_id": user_id
                }
            except Exception as e:
                # 更新状态为失败
                self.update_embedding_status("failed", user_id, db)

                logger.error(
                    f"Failed to build embeddings for user {user_id}: {e}")
                return {
                    "message": "Failed to build embeddings",
                    "processed_count": 0,
                    "user_id": user_id
                }

        except Exception as e:
            logger.error(f"Error building embeddings for user {user_id}: {e}")
            self.update_embedding_status("failed", user_id, db)
            raise e
        finally:
            db.close()

    def build_embeddings_for_all_users(self):
        """为所有用户构建embedding向量"""
        db = self.get_db()

        try:
            # 更新状态为构建中（使用全局状态）
            self.update_embedding_status("building", None, db)

            # 获取所有术语
            terms = db.query(Term).all()

            if not terms:
                logger.info("No terms found")
                self.update_embedding_status("completed", None, db)
                return {"message": "No terms to process", "processed_count": 0}

            logger.info(
                f"Building embeddings for {len(terms)} terms from all users")

            # 使用TermMatcher来重建索引，确保使用相同的embedding方法
            from term_matching.term_matcher import TermMatcher

            # 准备术语数据（只使用英文，与match时保持一致）
            terms_data = [
                {
                    "term_id": term.term_id,
                    "en": term.en
                }
                for term in terms
            ]

            try:
                # 使用TermMatcher重建索引
                matcher = TermMatcher()
                matcher.build_index_from_terms(terms_data)

                # 更新状态为成功
                self.update_embedding_status("completed", None, db)

                logger.info(
                    f"Successfully built embeddings for {len(terms)} terms")
                return {
                    "message": "Embeddings built successfully",
                    "processed_count": len(terms)
                }
            except Exception as e:
                # 更新状态为失败
                self.update_embedding_status("failed", None, db)

                logger.error(f"Failed to build embeddings: {e}")
                return {
                    "message": "Failed to build embeddings",
                    "processed_count": 0
                }

        except Exception as e:
            logger.error(f"Error building embeddings: {e}")
            self.update_embedding_status("failed", None, db)
            raise e
        finally:
            db.close()

    def search_similar_terms(self, query: str, top_k: int = 5, threshold: float = 0.7):
        """搜索相似术语"""
        try:
            from term_matching.term_matcher import TermMatcher

            # 使用TermMatcher进行搜索
            matcher = TermMatcher()
            matched_term_ids = matcher.match_terms(
                [query],
                similarity_threshold=threshold,
                top_k=top_k
            )

            # 获取匹配的term_id列表
            if matched_term_ids and matched_term_ids[0]:
                # 简化返回格式
                return [(term_id, 0.8) for term_id in matched_term_ids[0]]
            else:
                return []

        except Exception as e:
            logger.error(f"Error searching similar terms: {e}")
            raise e

    def get_embedding_stats(self):
        """获取embedding统计信息"""
        try:
            from term_matching.term_matcher import TermMatcher

            # 使用TermMatcher获取统计信息
            matcher = TermMatcher()
            index_stats = matcher.get_index_stats()

            return {
                "total_vectors": index_stats.get("total_vectors", 0),
                "embedding_dimension": index_stats.get("embedding_dimension", 1024),
                "mapped_terms": index_stats.get("mapped_terms", 0),
                "index_type": index_stats.get("index_type", "Unknown"),
                "is_loaded": index_stats.get("is_loaded", False)
            }
        except Exception as e:
            logger.error(f"Error getting embedding stats: {e}")
            raise e
