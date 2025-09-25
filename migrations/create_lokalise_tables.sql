-- Lokalise Keys 表创建脚本（硬删除版本）
-- 只包含核心字段：id, key_name, tags, project_id, project_name

CREATE TABLE IF NOT EXISTS lokalise_keys (
    id INT PRIMARY KEY COMMENT 'Lokalise Key ID',
    key_name VARCHAR(255) NOT NULL COMMENT 'Key名称',
    tags JSON COMMENT '标签列表',
    project_id VARCHAR(100) NOT NULL COMMENT 'Lokalise项目ID',
    project_name VARCHAR(255) NOT NULL COMMENT '项目名称',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lokalise Keys表';

-- 创建索引
CREATE INDEX idx_project_id ON lokalise_keys(project_id);
CREATE INDEX idx_key_name ON lokalise_keys(key_name);
CREATE INDEX idx_project_key ON lokalise_keys(project_id, key_name);
