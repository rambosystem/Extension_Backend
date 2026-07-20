-- terms 表索引对齐
--
-- 说明：线上 edge_extension_db 的 terms 表已存在以下索引
--   idx_user_id     (user_id)
--   idx_en          (en)
--   idx_created_at  (created_at)
--   idx_user_en     (user_id, en)
-- 本文件仅用于「缺失这些索引的环境」补齐（如全新搭建的库）。
-- 对已存在的库无需执行——模型 app/models/models.py 已声明同名索引，
-- create_all() 会在新库自动创建。
--
-- MySQL 无 CREATE INDEX IF NOT EXISTS，重复执行会报 1061 Duplicate key name，
-- 属预期（说明索引已存在），可忽略。

CREATE INDEX idx_user_id ON terms(user_id);
CREATE INDEX idx_en ON terms(en);
CREATE INDEX idx_created_at ON terms(created_at);
CREATE INDEX idx_user_en ON terms(user_id, en);

-- 验证
SHOW INDEX FROM terms;
