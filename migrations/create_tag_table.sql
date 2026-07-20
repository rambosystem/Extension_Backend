-- 创建 Lokalise Tag 表
-- 独立维护，不与其他表关联，只存储tag名称和使用次数

CREATE TABLE IF NOT EXISTS lokalise_tags (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    tag_name VARCHAR(255) NOT NULL COMMENT '标签名称',
    project_id VARCHAR(100) NOT NULL COMMENT '项目ID',
    usage_count INT DEFAULT 0 NOT NULL COMMENT '使用次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_tag_project (tag_name, project_id),
    INDEX idx_project_id (project_id),
    INDEX idx_tag_name (tag_name),
    INDEX idx_project_tag (project_id, tag_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Lokalise标签表';

