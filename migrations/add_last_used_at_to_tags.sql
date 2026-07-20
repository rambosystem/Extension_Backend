-- 添加 last_used_at 字段到 lokalise_tags 表
-- 用于记录tag的最后使用时间，支持按最近使用排序

ALTER TABLE lokalise_tags 
ADD COLUMN last_used_at TIMESTAMP NULL COMMENT '最后使用时间（用于自动补全排序，优先显示最近使用的tags）' 
AFTER usage_count;

-- 创建索引以优化按最近使用时间查询
CREATE INDEX idx_last_used_at ON lokalise_tags(last_used_at);
CREATE INDEX idx_project_last_used ON lokalise_tags(project_id, last_used_at);

