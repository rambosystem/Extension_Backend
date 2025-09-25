from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging
from datetime import datetime

from app.db.database import get_db
from app.models.models import LokaliseKey
from app.models.schemas import (
    LokaliseKeyCreate, 
    LokaliseKeyUpdate, 
    LokaliseWebhookResponse,
    LokaliseKeysResponse,
    LokaliseKeyResponse
)

router = APIRouter(prefix="/lokalise", tags=["lokalise"])
logger = logging.getLogger(__name__)


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
            project_name=project_name
        )
        
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        
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
                        project_name=project_name
                    )
                    
                    db.add(new_key)
                    added_count += 1
        
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
                    # 更新字段
                    existing_key.key_name = key_name
                    existing_key.tags = tags
                    existing_key.project_name = project_name
                    
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
        
        # 更新字段
        existing_key.key_name = key_name
        existing_key.tags = tags
        existing_key.project_name = project_name
        
        db.commit()
        db.refresh(existing_key)
        
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
                        # 硬删除（物理删除）
                        
                        db.delete(existing_key)
                        deleted_count += 1
                        
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