-- 删除 embedding 表
--
-- 背景：term 匹配已从「BGE-Large + FAISS」重构为轻量字符串匹配
-- （term_matching/string_matcher.py），实时读 DB、无预建索引，
-- 不再需要记录 embedding 构建状态。相关模型 Embedding 已从
-- app/models/models.py 移除。
--
-- 本文件用于清理线上库中遗留的 embedding 表。
-- 表不存在时 IF EXISTS 不会报错，可安全重复执行。

DROP TABLE IF EXISTS embedding;
