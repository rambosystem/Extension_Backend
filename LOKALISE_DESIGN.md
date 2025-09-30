# Lokalise Webhook API 设计方案

## 概述

基于您提供的Lokalise webhook数据，我设计了一个完整的webhook API系统，支持三种事件类型：添加、修改、删除。

## 系统架构

### 1. 数据库设计

#### Lokalise Keys 表 (`lokalise_keys`)
```sql
CREATE TABLE lokalise_keys (
    id INT PRIMARY KEY COMMENT 'Lokalise Key ID',
    key_name VARCHAR(255) NOT NULL COMMENT 'Key名称',
    tags JSON COMMENT '标签列表',
    project_id VARCHAR(100) NOT NULL COMMENT 'Lokalise项目ID',
    project_name VARCHAR(255) NOT NULL COMMENT '项目名称',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    deleted_at DATETIME NULL COMMENT '删除时间'
);
```

**主键设计：**
- `id` + `project_id` 作为复合主键，确保每个项目中的key ID唯一
- 支持软删除（通过`deleted_at`字段）

**索引设计：**
- `idx_project_id`: 按项目ID查询
- `idx_key_name`: 按key名称查询
- `idx_project_key`: 复合索引，优化项目+key查询

**简化说明：**
- 移除了冗余字段：`base_value`, `filenames`, `hidden`, `screenshots`
- 移除了webhook日志表，减少系统复杂度
- 只保留核心业务字段，提高性能和维护性

### 2. API 设计

#### 主要端点

1. **POST /lokalise/webhook** - 处理webhook事件
2. **GET /lokalise/keys/{project_id}** - 获取项目下的所有keys
3. **GET /lokalise/keys/{project_id}/{key_id}** - 获取指定key
4. **POST /lokalise/search-by-names** - 根据key名称列表搜索keys（大小写敏感）
5. **GET /lokalise/** - API状态检查

#### 支持的事件类型

1. **project.key.added** - 添加新key
2. **project.key.modified** - 修改key
3. **project.keys.deleted** - 删除key

### 3. 数据模型

#### Pydantic 模型
- `LokaliseKeyCreate` - 创建key模型
- `LokaliseKeyUpdate` - 更新key模型
- `LokaliseKeyResponse` - 响应模型
- `LokaliseWebhookRequest` - webhook请求模型
- `LokaliseWebhookResponse` - webhook响应模型
- `KeyNameSearchRequest` - 按名称搜索请求模型（大小写敏感）
- `KeyNameSearchResponse` - 按名称搜索响应模型
- `KeySearchResult` - 单个搜索结果模型

#### SQLAlchemy 模型
- `LokaliseKey` - 数据库模型
- `LokaliseWebhookLog` - 日志模型

### 4. 服务层设计

#### LokaliseService 类
- `add_key()` - 添加key
- `update_key()` - 更新key
- `delete_key()` - 软删除key
- `get_key()` - 获取单个key
- `get_keys_by_project()` - 获取项目所有keys
- `log_webhook_request()` - 记录webhook日志
- `parse_webhook_data()` - 解析webhook数据

### 5. 错误处理

#### 异常处理策略
- 数据库操作异常回滚
- 详细的错误日志记录
- HTTP状态码标准化
- 友好的错误消息

#### 日志记录
- 所有webhook请求都会记录到日志表
- 处理状态跟踪（pending/success/failed）
- 错误信息详细记录

### 6. 数据流程

#### Webhook 处理流程
1. 接收webhook请求
2. 记录请求日志
3. 解析请求数据
4. 根据事件类型调用相应处理函数
5. 执行数据库操作
6. 更新日志状态
7. 返回响应

#### 事件处理逻辑

**添加事件 (project.key.added):**
```python
# 检查key是否已存在
# 创建新key记录
# 返回成功响应
```

**修改事件 (project.key.modified):**
```python
# 查找现有key
# 更新key信息
# 返回成功/失败响应
```

**删除事件 (project.keys.deleted):**
```python
# 查找现有key
# 执行软删除
# 返回成功/失败响应
```

### 7. 测试方案

#### 测试脚本功能
- API状态测试
- 三种事件类型测试
- 查询接口测试
- 异常情况测试

#### 测试数据
基于您提供的真实webhook数据：
- Key添加：apple, pie, water
- Key修改：Webhooker (原Webhook)
- Key删除：批量删除事件

### 8. 部署说明

#### 数据库迁移
```bash
# 执行SQL脚本创建表
mysql -u username -p database_name < migrations/create_lokalise_tables.sql
```

#### 启动服务
```bash
# 启动FastAPI服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 测试API
```bash
# 运行测试脚本
python test_lokalise_api.py
```

### 9. 特性亮点

1. **完整的CRUD操作** - 支持key的增删改查
2. **软删除机制** - 数据安全，支持恢复
3. **详细的日志记录** - 便于调试和监控
4. **错误处理完善** - 异常情况处理完备
5. **RESTful API设计** - 符合REST规范
6. **数据验证** - Pydantic模型验证
7. **索引优化** - 数据库查询性能优化
8. **测试完备** - 包含完整的测试用例

### 10. 搜索功能详解

#### 按名称搜索接口 (POST /lokalise/search-by-names)

**功能描述：**
根据提供的key名称列表搜索匹配的keys，大小写敏感搜索。

**请求参数：**
```json
{
  "project_id": "project123",
  "key_names": ["key1", "KEY2", "Key3"]
}
```

**响应格式：**
```json
{
  "success": true,
  "message": "Found 2 keys, 1 keys not found: ['Key3']",
  "total_found": 2,
  "results": [
    {
      "key_id": 123,
      "key_name": "key1",
      "tags": ["tag1", "tag2"]
    },
    {
      "key_id": 124,
      "key_name": "KEY2",
      "tags": ["tag3"]
    }
  ]
}
```

**搜索逻辑：**
- 精确匹配，区分大小写
- 限制在指定项目内搜索
- 数据库使用 `utf8mb4_bin` collation 支持大小写敏感查询

**性能优化：**
- 使用数据库索引 `idx_key_name` 提升查询性能
- 支持批量搜索，一次请求可搜索多个key名称

### 11. 扩展建议

1. **批量操作** - 支持批量添加/删除keys
2. **缓存机制** - 添加Redis缓存提升性能
3. **异步处理** - 使用Celery处理大量webhook
4. **监控告警** - 添加webhook处理失败告警
5. **API限流** - 防止webhook请求过载
6. **数据同步** - 与Lokalise API双向同步
7. **模糊搜索** - 支持部分匹配和正则表达式搜索
8. **搜索历史** - 记录用户搜索历史，提供搜索建议

## 总结

这个设计方案提供了：
- 完整的数据库设计
- 健壮的API实现
- 完善的错误处理
- 详细的日志记录
- 全面的测试覆盖

系统可以可靠地处理Lokalise的webhook事件，并提供完整的key管理功能。
