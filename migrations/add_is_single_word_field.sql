-- 添加 is_single_word 字段到 lokalise_keys 表
-- 用于优化单词语key的查询性能

-- 1. 添加字段
ALTER TABLE lokalise_keys 
ADD COLUMN is_single_word BOOLEAN DEFAULT FALSE COMMENT '是否为单词语（英文+数字）';

-- 2. 创建索引
CREATE INDEX idx_is_single_word ON lokalise_keys(is_single_word);
CREATE INDEX idx_project_single_word ON lokalise_keys(project_id, is_single_word);

-- 3. 更新现有数据，设置 is_single_word 标志
-- 只包含英文字母和数字的key标记为单词语
UPDATE lokalise_keys 
SET is_single_word = TRUE 
WHERE key_name REGEXP '^[a-zA-Z0-9]+$';

-- 4. 验证更新结果
SELECT 
    COUNT(*) as total_keys,
    SUM(CASE WHEN is_single_word = TRUE THEN 1 ELSE 0 END) as single_word_keys,
    SUM(CASE WHEN is_single_word = FALSE THEN 1 ELSE 0 END) as multi_word_keys
FROM lokalise_keys;
