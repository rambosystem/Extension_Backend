# 术语匹配

轻量字符串匹配器 `StringTermMatcher`，替代原「BGE-Large-EN + FAISS」语义方案。

## 特性

- **无模型、无 FAISS**：不加载任何深度模型，不依赖索引文件
- **实时读库**：匹配时直接从数据库读取候选术语，增删术语无需维护索引
- **归一化整词匹配**：小写化 + 非字母数字折叠，天然吸收大小写 / 空格 / 标点差异
- **最长优先、不重叠**：`budget scheduler` 优先于 `scheduler`
- **词边界保护**：`agent` 不会命中 `agentic`

## 适用前提

术语是明确的词 / 短语（产品名词等），只需字面 / 近似匹配，**不需要语义泛化**。
术语量小，直接实时构建匹配器即可。

## 用法

```python
from term_matching import StringTermMatcher

matcher = StringTermMatcher()
# terms 支持 ORM 对象或 (term_id, en) 元组
result = matcher.match_terms(["Set up the Budget Scheduler."], terms, top_k=10)
# -> [[term_id, ...]]  与输入等长，每项为命中的 term_id 列表
```

## 相关端点

`app/api/router/term_match.py`：`POST /term-match/match`、`GET /term-match/search`、
`POST /term-match/test`。
