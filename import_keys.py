#!/usr/bin/env python3
"""
Lokalise Keys 批量导入脚本
用于将 keys_data.json 中的全量数据导入到 lokalise_keys 表中
"""

import json
import sys
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from tqdm import tqdm

# 添加项目根目录到 Python 路径
sys.path.append('/home/ubuntu/project/extension_backend')

from app.db.database import get_db, engine
from app.models.models import LokaliseKey

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('import_keys.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 项目信息
PROJECT_ID = "2582110965ade9652de217.13653519"
PROJECT_NAME = "AmazonSearch"
BATCH_SIZE = 1000  # 批量处理大小


def load_keys_data(file_path: str) -> List[Dict[str, Any]]:
    """加载 keys_data.json 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"成功加载 {len(data)} 条 key 数据")
        return data
    except Exception as e:
        logger.error(f"加载数据文件失败: {e}")
        raise


def check_existing_keys(db: Session, project_id: str) -> set:
    """检查已存在的 key IDs"""
    try:
        existing_keys = db.query(LokaliseKey.id).filter(
            LokaliseKey.project_id == project_id
        ).all()
        existing_ids = {key.id for key in existing_keys}
        logger.info(f"项目中已存在 {len(existing_ids)} 个 keys")
        return existing_ids
    except Exception as e:
        logger.error(f"检查已存在 keys 失败: {e}")
        return set()


def import_keys_batch(db: Session, keys_data: List[Dict[str, Any]], 
                     project_id: str, project_name: str, 
                     existing_ids: set) -> tuple:
    """批量导入 keys"""
    new_keys = []
    skipped_count = 0
    error_count = 0
    
    for key_data in tqdm(keys_data, desc="处理 keys"):
        try:
            key_id = key_data['id']
            key_name = key_data['key_name']
            tags = key_data.get('tags', [])
            
            # 跳过已存在的 key
            if key_id in existing_ids:
                skipped_count += 1
                continue
            
            # 创建新的 LokaliseKey 对象
            new_key = LokaliseKey(
                id=key_id,
                key_name=key_name,
                tags=tags,
                project_id=project_id,
                project_name=project_name
            )
            
            new_keys.append(new_key)
            
        except Exception as e:
            logger.error(f"处理 key 数据失败: {key_data}, 错误: {e}")
            error_count += 1
            continue
    
    # 批量插入数据库
    if new_keys:
        try:
            db.bulk_save_objects(new_keys)
            db.commit()
            logger.info(f"成功插入 {len(new_keys)} 个新 keys")
        except IntegrityError as e:
            db.rollback()
            logger.error(f"批量插入失败，可能存在重复数据: {e}")
            # 尝试逐个插入
            success_count = 0
            for key in new_keys:
                try:
                    db.add(key)
                    db.commit()
                    success_count += 1
                except IntegrityError:
                    db.rollback()
                    logger.warning(f"跳过重复的 key: {key.id}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"插入 key {key.id} 失败: {e}")
            logger.info(f"逐个插入成功 {success_count} 个 keys")
        except Exception as e:
            db.rollback()
            logger.error(f"批量插入失败: {e}")
            raise
    
    return len(new_keys), skipped_count, error_count


def main():
    """主函数"""
    logger.info("开始导入 Lokalise Keys 数据")
    
    # 数据文件路径
    data_file = "/home/ubuntu/project/extension_backend/key_list/keys_data_amazon_search.json"
    
    try:
        # 加载数据
        keys_data = load_keys_data(data_file)
        
        # 获取数据库会话
        db = next(get_db())
        
        try:
            # 检查已存在的 keys
            existing_ids = check_existing_keys(db, PROJECT_ID)
            
            # 批量导入
            total_processed = 0
            total_skipped = 0
            total_errors = 0
            
            # 分批处理
            for i in range(0, len(keys_data), BATCH_SIZE):
                batch = keys_data[i:i + BATCH_SIZE]
                logger.info(f"处理批次 {i//BATCH_SIZE + 1}: {len(batch)} 条记录")
                
                new_count, skipped_count, error_count = import_keys_batch(
                    db, batch, PROJECT_ID, PROJECT_NAME, existing_ids
                )
                
                total_processed += new_count
                total_skipped += skipped_count
                total_errors += error_count
                
                # 更新已存在的 IDs 集合，避免重复检查
                for key_data in batch:
                    existing_ids.add(key_data['id'])
            
            # 输出统计信息
            logger.info("=" * 50)
            logger.info("导入完成统计:")
            logger.info(f"总数据量: {len(keys_data)}")
            logger.info(f"新增导入: {total_processed}")
            logger.info(f"跳过重复: {total_skipped}")
            logger.info(f"处理错误: {total_errors}")
            logger.info(f"项目ID: {PROJECT_ID}")
            logger.info(f"项目名称: {PROJECT_NAME}")
            logger.info("=" * 50)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"导入过程发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
