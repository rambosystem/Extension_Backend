# Term Match API 快速参考

## 主要接口

### 术语匹配
```bash
POST /term-match/match
```

**请求示例:**
```bash
curl -X POST "http://localhost:8000/term-match/match?similarity_threshold=0.7&top_k=10" \
  -H "Content-Type: application/json" \
  -d '["machine learning", "neural network"]'
```

**参数说明:**
- `similarity_threshold`: 相似度阈值 (0.0-1.0, 默认0.7)
- `top_k`: 最大返回数量 (1-50, 默认10)
- `max_ngram`: 最大N-gram长度 (1-5, 默认3)
- `user_id`: 用户ID过滤 (可选)

### 统计信息
```bash
GET /term-match/stats
```

### 测试接口
```bash
POST /term-match/test?text=machine learning&similarity_threshold=0.6&top_k=5
```

## 响应格式

**成功响应:**
```json
[
  [
    {
      "term_id": 1,
      "en": "machine learning",
      "cn": "机器学习",
      "jp": "機械学習"
    }
  ],
  [
    {
      "term_id": 2,
      "en": "neural network",
      "cn": "神经网络",
      "jp": "ニューラルネットワーク"
    }
  ]
]
```

## 编程语言示例

### Python
```python
import requests

response = requests.post(
    "http://localhost:8000/term-match/match",
    params={"similarity_threshold": 0.7, "top_k": 10},
    json=["machine learning", "neural network"]
)
results = response.json()
```

### JavaScript
```javascript
const response = await fetch('/term-match/match?similarity_threshold=0.7&top_k=10', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(["machine learning", "neural network"])
});
const results = await response.json();
```

### Java
```java
HttpClient client = HttpClient.newHttpClient();
String json = "[\"machine learning\", \"neural network\"]";
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("http://localhost:8000/term-match/match?similarity_threshold=0.7&top_k=10"))
    .header("Content-Type", "application/json")
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();
HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
```

## 最佳实践

1. **批量处理**: 一次发送多个文本而不是逐个处理
2. **参数调优**: 
   - 严格匹配: `similarity_threshold=0.8`
   - 一般匹配: `similarity_threshold=0.7`
   - 宽松匹配: `similarity_threshold=0.6`
3. **性能监控**: 定期调用 `/term-match/stats` 监控性能

## 错误处理

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 参数错误 |
| 500 | 服务错误 |

常见错误: 模型路径错误、索引未加载、参数范围错误 