#!/usr/bin/env python3
"""
Lokalise Tags 数据迁移脚本
从现有的 lokalise_keys 表中提取所有 tags，并初始化 lokalise_tags 表
"""

import sys
import logging
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import text

# 添加项目根目录到 Python 路径
sys.path.append('/home/ubuntu/project/extension_backend')

from app.db.database import get_db, engine
from app.models.models import LokaliseKey, LokaliseTag

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migrate_tags.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def extract_tags_from_keys(db: Session) -> dict:
    """
    从所有keys中提取tags并统计使用次数
    
    Returns:
        dict: {project_id: {tag_name: count}}
    """
    logger.info("开始从keys表中提取tags...")
    
    # 查询所有keys
    keys = db.query(LokaliseKey).all()
    logger.info(f"找到 {len(keys)} 条keys记录")
    
    # 统计每个项目下每个tag的使用次数
    tag_stats = defaultdict(lambda: defaultdict(int))
    
    for key in keys:
        if key.tags and isinstance(key.tags, list):
            for tag in key.tags:
                if tag and isinstance(tag, str) and tag.strip():
                    tag_name = tag.strip()
                    tag_stats[key.project_id][tag_name] += 1
    
    logger.info(f"提取完成，共 {len(tag_stats)} 个项目，总计 {sum(len(tags) for tags in tag_stats.values())} 个唯一tags")
    
    return tag_stats


def initialize_tag_table(db: Session, tag_stats: dict):
    """
    初始化tag表，插入或更新tags
    
    Args:
        db: 数据库会话
        tag_stats: {project_id: {tag_name: count}}
    """
    logger.info("开始初始化tag表...")
    
    total_inserted = 0
    total_updated = 0
    total_errors = 0
    
    for project_id, tags in tag_stats.items():
        logger.info(f"处理项目 {project_id}，共 {len(tags)} 个tags")
        
        for tag_name, count in tags.items():
            try:
                # 查找是否已存在
                existing_tag = db.query(LokaliseTag).filter(
                    LokaliseTag.tag_name == tag_name,
                    LokaliseTag.project_id == project_id
                ).first()
                
                if existing_tag:
                    # 更新使用次数
                    existing_tag.usage_count = count
                    total_updated += 1
                else:
                    # 创建新tag
                    new_tag = LokaliseTag(
                        tag_name=tag_name,
                        project_id=project_id,
                        usage_count=count
                    )
                    db.add(new_tag)
                    total_inserted += 1
                    
            except Exception as e:
                logger.error(f"处理tag失败: project_id={project_id}, tag_name={tag_name}, error={str(e)}")
                total_errors += 1
                continue
    
    # 提交所有更改
    try:
        db.commit()
        logger.info(f"Tag表初始化完成:")
        logger.info(f"  - 新增: {total_inserted} 个tags")
        logger.info(f"  - 更新: {total_updated} 个tags")
        logger.info(f"  - 错误: {total_errors} 个tags")
    except Exception as e:
        db.rollback()
        logger.error(f"提交失败: {str(e)}")
        raise


def verify_migration(db: Session):
    """验证迁移结果"""
    logger.info("验证迁移结果...")
    
    # 统计tag表数据
    total_tags = db.query(LokaliseTag).count()
    projects = db.query(LokaliseTag.project_id).distinct().all()
    project_count = len(projects)
    
    logger.info(f"Tag表统计:")
    logger.info(f"  - 总tags数: {total_tags}")
    logger.info(f"  - 项目数: {project_count}")
    
    # 按项目统计
    for project_id, in projects:
        project_tags = db.query(LokaliseTag).filter(
            LokaliseTag.project_id == project_id
        ).count()
        total_usage = db.query(LokaliseTag).filter(
            LokaliseTag.project_id == project_id
        ).with_entities(
            text("SUM(usage_count)")
        ).scalar() or 0
        
        logger.info(f"  - 项目 {project_id}: {project_tags} 个tags, 总使用次数 {total_usage}")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始迁移 Lokalise Tags 数据")
    logger.info("=" * 60)
    
    db = next(get_db())
    
    try:
        # 1. 从keys表中提取tags
        tag_stats = extract_tags_from_keys(db)
        
        # 2. 初始化tag表
        initialize_tag_table(db, tag_stats)
        
        # 3. 验证迁移结果
        verify_migration(db)
        
        logger.info("=" * 60)
        logger.info("迁移完成！")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"迁移失败: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

