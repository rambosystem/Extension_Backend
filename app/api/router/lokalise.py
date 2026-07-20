from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc
from typing import Dict, Any
import logging
import re
from datetime import datetime

from app.db.database import get_db
from app.models.models import LokaliseKey, LokaliseTag
from app.models.schemas import (
    LokaliseKeyCreate, 
    LokaliseKeyUpdate, 
    LokaliseWebhookResponse,
    LokaliseKeysResponse,
    LokaliseKeyResponse,
    KeyNameSearchRequest,
    KeyNameSearchResponse,
    KeySearchResult,
    KeyAutocompleteRequest,
    KeyAutocompleteResponse,
    KeyAutocompleteResult,
    TagAutocompleteRequest,
    TagAutocompleteResponse,
    TagAutocompleteResult
)

router = APIRouter(prefix="/lokalise", tags=["lokalise"])
logger = logging.getLogger(__name__)


def is_single_word_key(key_name: str) -> bool:
    """
    判断key是否为单词语（英文+数字，如abc123）
    
    Args:
        key_name: key名称
        
    Returns:
        bool: 是否为单词语
    """
    if not key_name:
        return False
    
    # 使用正则表达式匹配：只包含英文字母和数字，且不包含分隔符
    # 匹配模式：^[a-zA-Z0-9]+$ 且长度大于0
    pattern = r'^[a-zA-Z0-9]+$'
    return bool(re.match(pattern, key_name))


def sync_tags(db: Session, project_id: str, tags: list, increment: bool = True):
    """
    同步tag表：更新tags的使用次数和最后使用时间
    
    Args:
        db: 数据库会话
        project_id: 项目ID
        tags: tag列表
        increment: True表示增加计数，False表示减少计数

    Note:
        Session 使用 autoflush=False。同一事务内多个 key 共享新 tag 时，
        若每次都 INSERT，会在 commit 时触发 uk_tag_project 唯一约束冲突，
        导致整批 keys 回滚。因此用 session 级缓存保证每个 tag 只创建一次。
    """
    if not tags or not isinstance(tags, list):
        return
    
    delta = 1 if increment else -1
    current_time = datetime.now()
    # 同一 DB session / 事务内复用，避免批量 webhook 重复 INSERT 同一 tag
    tag_cache: Dict[tuple, LokaliseTag] = db.info.setdefault('_lokalise_tag_cache', {})
    
    for tag in tags:
        if not tag or not isinstance(tag, str) or not tag.strip():
            continue
        
        tag_name = tag.strip()
        cache_key = (project_id, tag_name)
        
        try:
            existing_tag = tag_cache.get(cache_key)
            if existing_tag is None:
                existing_tag = db.query(LokaliseTag).filter(
                    LokaliseTag.tag_name == tag_name,
                    LokaliseTag.project_id == project_id
                ).first()
                if existing_tag is not None:
                    tag_cache[cache_key] = existing_tag
            
            if existing_tag is not None:
                # 更新使用次数
                new_count = existing_tag.usage_count + delta
                if new_count < 0:
                    new_count = 0  # 防止负数
                existing_tag.usage_count = new_count
                # 更新最后使用时间（只在increment时更新）
                if increment:
                    existing_tag.last_used_at = current_time
            else:
                # 创建新tag记录（只在increment时创建）
                if increment:
                    new_tag = LokaliseTag(
                        tag_name=tag_name,
                        project_id=project_id,
                        usage_count=1,
                        last_used_at=current_time
                    )
                    db.add(new_tag)
                    tag_cache[cache_key] = new_tag
        except Exception as e:
            logger.error(f"同步tag失败: project_id={project_id}, tag_name={tag_name}, error={str(e)}")
            # 继续处理其他tags，不中断流程


@router.get("/")
async def get_lokalise():
    """获取Lokalise服务状态"""
    return {
        "message": "Lokalise Webhook API is running!",
        "version": "1.0.0",
        "supported_events": [
            "project.key.added", 
            "project.keys.added",
            "project.key.modified", 
            "project.keys.modified",
            "project.keys.deleted"
        ]
    }


@router.post("/webhook", response_model=LokaliseWebhookResponse)
async def webhook(request: Request, db: Session = Depends(get_db)):
    """
    处理Lokalise Webhook事件
    
    支持的事件类型：
    - project.key.added: 添加单个key
    - project.keys.added: 批量添加keys
    - project.key.modified: 修改单个key
    - project.keys.modified: 批量修改keys
    - project.keys.deleted: 删除keys
    """
    logger.info('==========webhook==========')
    
    try:
        # 获取并解析JSON请求体
        data = await request.json()
    except Exception as json_error:
        logger.error(f"Error parsing JSON: {str(json_error)}")
        # JSON解析失败也返回200，避免Lokalise重试
        return LokaliseWebhookResponse(
            success=False,
            message=f"Invalid JSON format: {str(json_error)}",
            event_type='unknown',
            key_id=None,
            project_id=None
        )

    try:
        logger.info(f"Received webhook: {data}")
        
        event = data.get('event', '')
        key_data = data.get('key', {})
        keys_data = data.get('keys', [])  # 删除事件中的keys数组
        project_data = data.get('project', {})
        
        # 根据事件类型处理
        if event == 'project.key.added':
            result = await handle_key_added(db, key_data, project_data)
        elif event == 'project.keys.added':
            result = await handle_keys_added(db, keys_data, project_data)
        elif event == 'project.key.modified':
            result = await handle_key_modified(db, key_data, project_data)
        elif event == 'project.keys.modified':
            result = await handle_keys_modified(db, keys_data, project_data)
        elif event == 'project.keys.deleted':
            result = await handle_keys_deleted(db, key_data, keys_data, project_data)
        else:
            # 不支持的事件类型，返回200但标记为不支持
            logger.warning(f"Unsupported event type: {event}")
            result = LokaliseWebhookResponse(
                success=False,
                message=f"Unsupported event type: {event}",
                event_type=event,
                key_id=None,
                project_id=project_data.get('id')
            )
        
        logger.info(f"Successfully processed webhook event: {event}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        # 仍返回200，避免Lokalise无限重试；但不再误报为 JSON 解析失败
        return LokaliseWebhookResponse(
            success=False,
            message=f"Webhook processing failed: {str(e)}",
            event_type=data.get('event', 'unknown') if isinstance(data, dict) else 'unknown',
            key_id=None,
            project_id=(data.get('project') or {}).get('id') if isinstance(data, dict) else None
        )


async def handle_key_added(db: Session, key_data: Dict[str, Any], project_data: Dict[str, Any]) -> LokaliseWebhookResponse:
    """处理key添加事件"""
    try:
        key_id = key_data.get('id')
        key_name = key_data.get('name')
        tags = key_data.get('tags', [])
        project_id = project_data.get('id')
        project_name = project_data.get('name')
        
        # 检查是否已存在
        existing_key = db.query(LokaliseKey).filter(
            LokaliseKey.id == key_id,
            LokaliseKey.project_id == project_id,
        ).first()
        
        if existing_key:
            logger.warning(f"Key {key_id} already exists in project {project_id}")
            return LokaliseWebhookResponse(
                success=True,
                message=f"Key '{key_name}' already exists",
                event_type='project.key.added',
                key_id=key_id,
                project_id=project_id
            )
        
        # 创建新key
        new_key = LokaliseKey(
            id=key_id,
            key_name=key_name,
            tags=tags,
            project_id=project_id,
            project_name=project_name,
            is_single_word=is_single_word_key(key_name)
        )
        
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        
        # 同步tag表：增加tags的使用次数
        if tags:
            sync_tags(db, project_id, tags, increment=True)
            db.commit()
        
        logger.info(f"Successfully added key {key_id}: {key_name}")
        return LokaliseWebhookResponse(
            success=True,
            message=f"Key '{key_name}' added successfully",
            event_type='project.key.added',
            key_id=key_id,
            project_id=project_id
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error handling key added event: {str(e)}")
        raise e


async def handle_keys_added(db: Session, keys_data: list, project_data: Dict[str, Any]) -> LokaliseWebhookResponse:
    """处理批量key添加事件"""
    try:
        
        project_id = project_data.get('id')
        project_name = project_data.get('name')
        
        if not keys_data or len(keys_data) == 0:
            return LokaliseWebhookResponse(
                success=False,
                message="No keys provided in batch add request",
                event_type='project.keys.added',
                key_id=None,
                project_id=project_id
            )
        
        added_count = 0
        skipped_count = 0
        
        for key_info in keys_data:
            key_id = key_info.get('id')
            key_name = key_info.get('name')
            tags = key_info.get('tags', [])
            
            
            if key_id:
                # 检查是否已存在
                existing_key = db.query(LokaliseKey).filter(
                    LokaliseKey.id == key_id,
                    LokaliseKey.project_id == project_id,
                ).first()
                
                if existing_key:
                    skipped_count += 1
                else:
                    # 创建新key
                    new_key = LokaliseKey(
                        id=key_id,
                        key_name=key_name,
                        tags=tags,
                        project_id=project_id,
                        project_name=project_name,
                        is_single_word=is_single_word_key(key_name)
                    )
                    
                    db.add(new_key)
                    added_count += 1
                    
                    # 同步tag表：增加tags的使用次数
                    if tags:
                        sync_tags(db, project_id, tags, increment=True)
        
        # 提交所有添加操作
        db.commit()
        
        message = f"Successfully added {added_count} key(s)"
        if skipped_count > 0:
            message += f", {skipped_count} key(s) already existed"
        
        logger.info(f"Batch add completed: {message}")
        return LokaliseWebhookResponse(
            success=True,
            message=message,
            event_type='project.keys.added',
            key_id=None,  # 批量操作，不返回单个key_id
            project_id=project_id
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error handling batch keys added event: {str(e)}")
        raise e


async def handle_keys_modified(db: Session, keys_data: list, project_data: Dict[str, Any]) -> LokaliseWebhookResponse:
    """处理批量key修改事件"""
    try:
        
        project_id = project_data.get('id')
        project_name = project_data.get('name')
        
        if not keys_data or len(keys_data) == 0:
            return LokaliseWebhookResponse(
                success=False,
                message="No keys provided in batch modify request",
                event_type='project.keys.modified',
                key_id=None,
                project_id=project_id
            )
        
        modified_count = 0
        not_found_count = 0
        
        for key_info in keys_data:
            key_id = key_info.get('id')
            key_name = key_info.get('name')
            tags = key_info.get('tags', [])
            
            
            if key_id:
                # 查找现有key
                existing_key = db.query(LokaliseKey).filter(
                    LokaliseKey.id == key_id,
                    LokaliseKey.project_id == project_id,
                ).first()
                
                if existing_key:
                    # 获取旧的tags，用于同步tag表
                    old_tags = existing_key.tags if existing_key.tags else []
                    
                    # 更新字段
                    existing_key.key_name = key_name
                    existing_key.tags = tags
                    existing_key.project_name = project_name
                    existing_key.is_single_word = is_single_word_key(key_name)
                    
                    # 同步tag表：减少旧tags的计数，增加新tags的计数
                    if old_tags:
                        sync_tags(db, project_id, old_tags, increment=False)
                    if tags:
                        sync_tags(db, project_id, tags, increment=True)
                    
                    modified_count += 1
                else:
                    not_found_count += 1
        
        # 提交所有修改操作
        db.commit()
        
        message = f"Successfully modified {modified_count} key(s)"
        if not_found_count > 0:
            message += f", {not_found_count} key(s) not found"
        
        logger.info(f"Batch modify completed: {message}")
        return LokaliseWebhookResponse(
            success=True,
            message=message,
            event_type='project.keys.modified',
            key_id=None,  # 批量操作，不返回单个key_id
            project_id=project_id
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error handling batch keys modified event: {str(e)}")
        raise e


async def handle_key_modified(db: Session, key_data: Dict[str, Any], project_data: Dict[str, Any]) -> LokaliseWebhookResponse:
    """处理key修改事件"""
    try:
        key_id = key_data.get('id')
        key_name = key_data.get('name')
        tags = key_data.get('tags', [])
        project_id = project_data.get('id')
        project_name = project_data.get('name')
        
        # 查找现有key
        existing_key = db.query(LokaliseKey).filter(
            LokaliseKey.id == key_id,
            LokaliseKey.project_id == project_id,
        ).first()
        
        if not existing_key:
            logger.warning(f"Key {key_id} not found in project {project_id}")
            return LokaliseWebhookResponse(
                success=False,
                message=f"Key {key_id} not found",
                event_type='project.key.modified',
                key_id=key_id,
                project_id=project_id
            )
        
        # 获取旧的tags，用于同步tag表
        old_tags = existing_key.tags if existing_key.tags else []
        
        # 更新字段
        existing_key.key_name = key_name
        existing_key.tags = tags
        existing_key.project_name = project_name
        existing_key.is_single_word = is_single_word_key(key_name)
        
        db.commit()
        db.refresh(existing_key)
        
        # 同步tag表：减少旧tags的计数，增加新tags的计数
        if old_tags:
            sync_tags(db, project_id, old_tags, increment=False)
        if tags:
            sync_tags(db, project_id, tags, increment=True)
        db.commit()
        
        logger.info(f"Successfully updated key {key_id}: {key_name}")
        return LokaliseWebhookResponse(
            success=True,
            message=f"Key '{key_name}' updated successfully",
            event_type='project.key.modified',
            key_id=key_id,
            project_id=project_id
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error handling key modified event: {str(e)}")
        raise e


async def handle_keys_deleted(db: Session, key_data: Dict[str, Any], keys_data: list, project_data: Dict[str, Any]) -> LokaliseWebhookResponse:
    """处理key删除事件"""
    try:
        # 打印详细的删除请求信息
        
        project_id = project_data.get('id')
        
        # 处理keys数组中的每个key
        if keys_data and len(keys_data) > 0:
            deleted_count = 0
            failed_keys = []
            
            for key_info in keys_data:
                key_id = key_info.get('id')
                key_name = key_info.get('name', 'Unknown')
                
                
                if key_id:
                    # 查找现有key
                    existing_key = db.query(LokaliseKey).filter(
                        LokaliseKey.id == key_id,
                        LokaliseKey.project_id == project_id,
                    ).first()
                    
                    
                    if existing_key:
                        # 获取tags，用于同步tag表
                        tags = existing_key.tags if existing_key.tags else []
                        
                        # 硬删除（物理删除）
                        db.delete(existing_key)
                        deleted_count += 1
                        
                        # 同步tag表：减少tags的使用次数
                        if tags:
                            sync_tags(db, project_id, tags, increment=False)
                        
                        logger.info(f"Successfully deleted key {key_id}")
                    else:
                        failed_keys.append(key_id)
                        logger.warning(f"Key {key_id} not found in project {project_id}")
                else:
                    failed_keys.append("unknown")
            
            # 提交所有删除操作
            db.commit()
            
            if deleted_count > 0:
                message = f"Successfully deleted {deleted_count} key(s)"
                if failed_keys:
                    message += f", {len(failed_keys)} key(s) not found"
                
                return LokaliseWebhookResponse(
                    success=True,
                    message=message,
                    event_type='project.keys.deleted',
                    key_id=None,  # 批量删除，不返回单个key_id
                    project_id=project_id
                )
            else:
                return LokaliseWebhookResponse(
                    success=False,
                    message=f"No keys were deleted. Failed keys: {failed_keys}",
                    event_type='project.keys.deleted',
                    key_id=None,
                    project_id=project_id
                )
        else:
            # 如果没有keys数组，尝试从key_data获取（向后兼容）
            key_id = key_data.get('id') if key_data else None
            
            if key_id:
                existing_key = db.query(LokaliseKey).filter(
                    LokaliseKey.id == key_id,
                    LokaliseKey.project_id == project_id,
                ).first()
                
                if existing_key:
                    existing_key.deleted_at = datetime.now()
                    db.commit()
                    
                    logger.info(f"Successfully deleted key {key_id}")
                    return LokaliseWebhookResponse(
                        success=True,
                        message=f"Key {key_id} deleted successfully",
                        event_type='project.keys.deleted',
                        key_id=key_id,
                        project_id=project_id
                    )
                else:
                    return LokaliseWebhookResponse(
                        success=False,
                        message=f"Key {key_id} not found",
                        event_type='project.keys.deleted',
                        key_id=key_id,
                        project_id=project_id
                    )
            else:
                # 完全没有key信息
                logger.warning("Keys deleted event received but no key information provided")
                return LokaliseWebhookResponse(
                    success=True,
                    message="Keys deleted event received (no key information)",
                    event_type='project.keys.deleted',
                    key_id=None,
                    project_id=project_id
                )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error handling keys deleted event: {str(e)}")
        raise e


@router.get("/keys/{project_id}", response_model=LokaliseKeysResponse)
async def get_project_keys(project_id: str, db: Session = Depends(get_db)):
    """获取项目下的所有Keys"""
    try:
        keys = db.query(LokaliseKey).filter(
            LokaliseKey.project_id == project_id
        ).all()
        
        return LokaliseKeysResponse(
            project_id=project_id,
            total_keys=len(keys),
            keys=keys
        )
        
    except Exception as e:
        logger.error(f"Error getting project keys: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting project keys: {str(e)}")


@router.get("/keys/{project_id}/{key_id}", response_model=LokaliseKeyResponse)
async def get_key(project_id: str, key_id: int, db: Session = Depends(get_db)):
    """获取指定的Key"""
    try:
        key = db.query(LokaliseKey).filter(
            LokaliseKey.id == key_id,
            LokaliseKey.project_id == project_id
        ).first()
        
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")
        
        return key
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting key: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting key: {str(e)}")


@router.post("/search-by-names", response_model=KeyNameSearchResponse)
async def search_keys_by_names(request: KeyNameSearchRequest, db: Session = Depends(get_db)):
    """
    根据 key_name 列表搜索 keys（大小写敏感）
    
    请求体:
    {
        "project_id": "project123",
        "key_names": ["key1", "key2", "key3"]
    }
    
    返回:
    {
        "success": true,
        "message": "Search completed",
        "total_found": 3,
        "results": [
            {
                "key_id": 123,
                "key_name": "key1",
                "tags": ["tag1", "tag2"]
            }
        ]
    }
    """
    try:
        if not request.key_names:
            return KeyNameSearchResponse(
                success=False,
                message="key_names list cannot be empty",
                total_found=0,
                results=[]
            )
        
        # 查询匹配的 keys（大小写敏感，限制在指定项目内）
        keys = db.query(LokaliseKey).filter(
            LokaliseKey.project_id == request.project_id,
            LokaliseKey.key_name.in_(request.key_names)
        ).all()
        
        # 转换为响应格式
        results = []
        for key in keys:
            result = KeySearchResult(
                key_id=key.id,
                key_name=key.key_name,
                tags=key.tags if key.tags else []
            )
            results.append(result)
        
        # 统计找到的 keys
        found_key_names = {key.key_name for key in keys}
        not_found = set(request.key_names) - found_key_names
        
        message = f"Found {len(results)} keys"
        if not_found:
            message += f", {len(not_found)} keys not found: {list(not_found)[:5]}{'...' if len(not_found) > 5 else ''}"
        
        logger.info(f"Search completed: {len(results)}/{len(request.key_names)} keys found")
        
        return KeyNameSearchResponse(
            success=True,
            message=message,
            total_found=len(results),
            results=results
        )
        
    except Exception as e:
        logger.error(f"Error searching keys by names: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/autocomplete/keys", response_model=KeyAutocompleteResponse)
async def autocomplete_keys(
    project_id: str,
    query: str,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """
    Key自动完成查询接口 - 根据key name进行前缀搜索
    
    限制条件:
    - 只返回单个词的key（不包含空格、下划线、点号、连字符等分隔符）
    - 必须是以输入字符开头的key（前缀匹配）
    - 按数字后缀倒序排列，方便找到最后一个key
    - 例如：输入 "wmt" 返回 "wmtkey401", "wmtkey400", "wmtkey99", "wmtkey1", "wmt"
    
    查询参数:
    - project_id: 项目ID
    - query: 搜索关键词（前缀）
    - limit: 返回结果数量限制，默认5个
    
    示例:
    GET /lokalise/autocomplete/keys?project_id=project123&query=app&limit=5
    
    返回:
    {
        "success": true,
        "message": "Found 5 results",
        "total_found": 5,
        "results": [
            {
                "key_id": 459870801,
                "key_name": "wmtkey401",
                "tags": ["Walmart"]
            },
            {
                "key_id": 459870800,
                "key_name": "wmtkey400",
                "tags": ["Walmart"]
            },
            {
                "key_id": 459870710,
                "key_name": "wmtkey99",
                "tags": ["Walmart"]
            },
            {
                "key_id": 459870701,
                "key_name": "wmtkey1",
                "tags": ["Walmart"]
            },
            {
                "key_id": 704646832,
                "key_name": "wmt",
                "tags": []
            }
        ]
    }
    """
    try:
        if not query or not query.strip():
            return KeyAutocompleteResponse(
                success=False,
                message="Query cannot be empty",
                total_found=0,
                results=[]
            )
        
        # 清理查询字符串
        query = query.strip()
        limit = min(limit, 20)  # 限制最大返回数量为20，提升性能
        
        # 使用is_single_word字段进行高效过滤，只返回单词语的key
        # 优化：使用前缀匹配（以输入字符开头）而不是包含匹配
        # 对于数字后缀的key，使用数字排序而不是字母排序
        # 使用原生SQL进行数字排序，确保找到最大的数字key
        from sqlalchemy import text
        
        sql_query = text("""
            SELECT * FROM lokalise_keys 
            WHERE project_id = :project_id 
              AND key_name LIKE :query_pattern 
              AND is_single_word = 1
            ORDER BY 
              CASE 
                WHEN key_name REGEXP :regex_pattern 
                THEN CAST(SUBSTRING(key_name, :prefix_length + 1) AS UNSIGNED)
                ELSE 0 
              END DESC,
              key_name DESC
            LIMIT :limit_count
        """)
        
        # 动态分析数据模式，自动识别完整的前缀
        # 查找所有以query开头的key，分析最常见的完整前缀模式
        pattern_analysis = text("""
            SELECT 
                key_name,
                SUBSTRING(key_name, 1, LENGTH(:query) + 1) as prefix_pattern
            FROM lokalise_keys 
            WHERE key_name LIKE :pattern 
              AND is_single_word = 1 
              AND key_name REGEXP CONCAT(:query, '[a-zA-Z]+[0-9]+$')
            ORDER BY key_name DESC
            LIMIT 10
        """)
        
        results = db.execute(pattern_analysis, {
            'query': query,
            'pattern': f"{query}%"
        }).fetchall()
        
        if results:
            # 分析最常见的完整前缀
            prefix_counts = {}
            for row in results:
                # 提取完整的前缀（去掉数字部分）
                import re
                match = re.match(r'^([a-zA-Z]+)\d+$', row.key_name)
                if match:
                    full_prefix = match.group(1)
                    prefix_counts[full_prefix] = prefix_counts.get(full_prefix, 0) + 1
            
            if prefix_counts:
                # 选择最常见的完整前缀
                common_prefix = max(prefix_counts, key=prefix_counts.get)
                regex_pattern = f"{common_prefix}[0-9]+$"
                prefix_length = len(common_prefix)
            else:
                # 回退到简单模式
                common_prefix = results[0].prefix_pattern
                regex_pattern = f"{common_prefix}[0-9]+$"
                prefix_length = len(common_prefix)
        else:
            # 尝试 "query + key" 模式
            test_query = f"{query}key%"
            test_count = db.execute(text("SELECT COUNT(*) FROM lokalise_keys WHERE key_name LIKE :pattern AND is_single_word = 1"), 
                                   {'pattern': test_query}).scalar()
            
            if test_count > 0:
                regex_pattern = f"{query}key[0-9]+$"
                prefix_length = len(query) + 3
            else:
                # 使用直接 "query + 数字" 模式
                regex_pattern = f"{query}[0-9]+$"
                prefix_length = len(query)
        
        keys = db.execute(sql_query, {
            'project_id': project_id,
            'query_pattern': f"{query}%",
            'regex_pattern': regex_pattern,
            'prefix_length': prefix_length,
            'limit_count': limit
        }).fetchall()
        
        # 转换为LokaliseKey对象
        key_objects = []
        for row in keys:
            # 处理tags字段，确保是列表类型
            tags = row.tags
            if isinstance(tags, str):
                import json
                try:
                    tags = json.loads(tags)
                except:
                    tags = []
            elif tags is None:
                tags = []
            
            key_obj = LokaliseKey(
                id=row.id,
                key_name=row.key_name,
                tags=tags,
                project_id=row.project_id,
                project_name=row.project_name,
                is_single_word=row.is_single_word
            )
            key_objects.append(key_obj)
        
        keys = key_objects
        
        # 转换为响应格式
        results = []
        for key in keys:
            result = KeyAutocompleteResult(
                key_id=key.id,
                key_name=key.key_name,
                tags=key.tags if key.tags else []
            )
            results.append(result)
        
        # 结果已经按key_name倒序排列，无需额外排序
        
        message = f"Found {len(results)} key(s)"
        if len(results) == limit:
            message += f" (limited to {limit})"
        
        logger.info(f"Key autocomplete search completed: {len(results)} results for query '{query}'")
        
        return KeyAutocompleteResponse(
            success=True,
            message=message,
            total_found=len(results),
            results=results
        )
        
    except Exception as e:
        logger.error(f"Error in key autocomplete search: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/autocomplete/tags", response_model=TagAutocompleteResponse)
async def autocomplete_tags(
    project_id: str,
    query: str,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """
    Tag自动完成查询接口 - 智能匹配tag名称，优先显示最近使用的tags
    
    匹配逻辑（优先级从高到低）:
    1. 前缀匹配：输入"comm"会优先匹配"common1"、"common"等以"comm"开头的tag
    2. 包含匹配：如果前缀匹配不足，会匹配包含查询字符串的tag（如"comm"匹配"mycommon"）
    3. 排序规则：
       - 前缀匹配 > 包含匹配
       - 完全匹配优先
       - 最近使用的tags优先（last_used_at降序）
       - 然后按使用频率（usage_count降序）
       - 最后按tag名称排序
    
    查询参数:
    - project_id: 项目ID
    - query: 搜索关键词（不区分大小写）
    - limit: 返回结果数量限制，默认5个，最大20个
    
    示例:
    GET /lokalise/autocomplete/tags?project_id=project123&query=comm&limit=5
    
    返回:
    {
        "success": true,
        "message": "Found 2 tag(s)",
        "total_found": 2,
        "results": [
            {
                "tag": "common1",
                "count": 10
            },
            {
                "tag": "common",
                "count": 5
            }
        ]
    }
    """
    try:
        if not query or not query.strip():
            return TagAutocompleteResponse(
                success=False,
                message="Query cannot be empty",
                total_found=0,
                results=[]
            )
        
        # 清理查询字符串
        query = query.strip().lower()
        limit = min(limit, 20)  # 限制最大返回数量为20，提升性能
        
        # 使用tag表进行高效查询，按最近使用时间排序
        # 1. 前缀匹配（最高优先级）- 使用SQL LIKE查询，按最近使用时间降序
        # 使用CASE WHEN处理NULL值，确保有last_used_at的排在前面
        from sqlalchemy import case
        prefix_tags = db.query(LokaliseTag).filter(
            LokaliseTag.project_id == project_id,
            LokaliseTag.tag_name.like(f"{query}%")
        ).order_by(
            case((LokaliseTag.last_used_at.is_(None), 1), else_=0),  # NULL值排在后面
            desc(LokaliseTag.last_used_at),  # 最近使用的优先
            desc(LokaliseTag.usage_count),  # 然后按使用频率
            asc(LokaliseTag.tag_name)  # 最后按名称排序
        ).all()
        
        # 2. 包含匹配（次优先级）- 如果前缀匹配不足，再查询包含匹配
        contains_tags = []
        if len(prefix_tags) < limit:
            # 获取已匹配的前缀tag名称（用于排除）
            prefix_tag_names = {tag.tag_name for tag in prefix_tags}
            
            # 使用SQL LIKE查询包含匹配（排除已匹配的前缀），按最近使用时间排序
            all_contains_tags = db.query(LokaliseTag).filter(
                LokaliseTag.project_id == project_id,
                LokaliseTag.tag_name.like(f"%{query}%")
            ).order_by(
                case((LokaliseTag.last_used_at.is_(None), 1), else_=0),  # NULL值排在后面
                desc(LokaliseTag.last_used_at),  # 最近使用的优先
                desc(LokaliseTag.usage_count),  # 然后按使用频率
                asc(LokaliseTag.tag_name)  # 最后按名称排序
            ).all()
            
            # 在Python中过滤掉前缀匹配的tags
            contains_tags = [tag for tag in all_contains_tags if tag.tag_name not in prefix_tag_names]
        
        # 智能匹配和排序逻辑
        prefix_matches = []  # 前缀匹配的tags
        contains_matches = []  # 包含匹配的tags
        
        for tag in prefix_tags:
            tag_lower = tag.tag_name.lower()
            is_exact_match = (tag_lower == query)
            prefix_matches.append({
                'tag': tag.tag_name,
                'count': tag.usage_count,
                'is_exact': is_exact_match,
                'length': len(tag.tag_name),
                'last_used_at': tag.last_used_at  # 保留最后使用时间用于排序
            })
        
        for tag in contains_tags:
            tag_lower = tag.tag_name.lower()
            # 计算匹配位置分数（越靠前越好）
            position = tag_lower.find(query)
            position_score = 1.0 / (position + 1) if position >= 0 else 0
            contains_matches.append({
                'tag': tag.tag_name,
                'count': tag.usage_count,
                'position_score': position_score,
                'length': len(tag.tag_name),
                'last_used_at': tag.last_used_at  # 保留最后使用时间用于排序
            })
        
        # 排序逻辑（已通过SQL排序，这里主要是为了完全匹配优先）：
        # 前缀匹配：完全匹配优先，然后保持SQL排序（最近使用 > 使用频率 > 名称）
        prefix_matches.sort(key=lambda x: (
            not x['is_exact'],  # 完全匹配优先（False < True）
            x['last_used_at'] is None,  # 有使用时间的优先
            -(x['last_used_at'].timestamp() if x['last_used_at'] else 0),  # 最近使用的优先
            -x['count'],  # 使用频率
            x['length']  # 长度
        ))
        
        # 包含匹配：保持SQL排序（最近使用 > 使用频率 > 名称），但考虑匹配位置
        contains_matches.sort(key=lambda x: (
            -x['position_score'],  # 匹配位置优先
            x['last_used_at'] is None,  # 有使用时间的优先
            -(x['last_used_at'].timestamp() if x['last_used_at'] else 0),  # 最近使用的优先
            -x['count'],  # 使用频率
            x['length']  # 长度
        ))
        
        # 合并结果：前缀匹配优先，然后是包含匹配
        sorted_tags = prefix_matches + contains_matches
        
        # 转换为响应格式
        results = []
        for item in sorted_tags[:limit]:
            result = TagAutocompleteResult(
                tag=item['tag'],
                count=item['count']
            )
            results.append(result)
        
        total_matched = len(prefix_matches) + len(contains_matches)
        message = f"Found {len(results)} tag(s)"
        if total_matched > limit:
            message += f" (showing top {limit} of {total_matched} matches)"
        
        logger.info(f"Tag autocomplete search completed: {len(results)} results for query '{query}'")
        
        return TagAutocompleteResponse(
            success=True,
            message=message,
            total_found=len(results),
            results=results
        )
        
    except Exception as e:
        logger.error(f"Error in tag autocomplete search: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")