# Batch Processing Design for pg_semantic_operators

## 当前问题

当前每个算子处理**单条数据**，批量数据会导致 N 次 API 调用：
```sql
SELECT * FROM images WHERE ai_image_filter('gpt-4o', url, '包含猫') = true;
```

这条查询会对每一行调用一次 LLM，效率极低。

---

## 批量处理方案

### 1. 核心设计思路

- **输入**：批量数据（数组/数组）
- **处理**：构建批量 prompt，让 LLM 一次性处理多条
- **输出**：JSON 数组结果（每条数据的判断结果或描述）

### 2. API 设计

```sql
-- 批量语义过滤（返回 JSON 数组）
ai_filter_batch(model_name, condition, row_data_array)
-- 例: ai_filter_batch('gpt-4o', '金额大于1000', '[{"金额":1500}, {"金额":500}]')

-- 批量图片描述（返回 JSON 数组）
ai_image_describe_batch(model_name, image_sources_array)
-- 例: ai_image_describe_batch('gpt-4o', ARRAY['url1', 'url2'])

-- 批量查询（返回 JSON 数组或单条 SQL）
ai_query_batch(model_name, prompts_array, schema_info)
```

### 3. Python 实现

```python
# pg_semantic_operators/operators/batch.py

import json
from typing import List, Dict, Any, Union
from ..client import call_model

def ai_filter_batch(
    model_name: str,
    condition: str,
    rows: Union[List[Dict], str]
) -> str:
    """
    批量语义过滤
    
    构建批量 prompt:
    ```
    判断以下每条数据是否满足条件: {condition}
    
    数据1: {row1}
    数据2: {row2}
    ...
    
    输出格式 (JSON 数组):
    [{"index": 0, "result": true/false}, {"index": 1, "result": true/false}, ...]
    ```
    """
    # 解析输入
    if isinstance(rows, str):
        rows = json.loads(rows)
    
    if not rows:
        return "[]"
    
    # 构建批量 prompt
    items = []
    for i, row in enumerate(rows):
        items.append(f"数据{i+1}: {json.dumps(row, ensure_ascii=False)}")
    
    data_section = "\n".join(items)
    
    prompt = f"""判断以下每条数据是否满足条件: {condition}

{data_section}

输出 JSON 数组格式，每条数据必须有 "result" 字段 (true/false):
[{{"index": 0, "result": true}}, {{"index": 1, "result": false}}, ...]"""

    result = call_model(model_name, prompt)
    
    # 解析结果
    try:
        # 尝试提取 JSON
        if "```json" in result:
            match = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
            if match:
                return match.group(1)
        if "[" in result:
            start = result.find("[")
            end = result.rfind("]") + 1
            return result[start:end]
    except:
        pass
    
    return "[]"


def ai_image_describe_batch(
    model_name: str,
    sources: Union[List[str], str]
) -> str:
    """
    批量图片描述
    
    使用多图输入 (目前仅 OpenAI 支持)
    """
    if isinstance(sources, str):
        # 处理 ARRAY['url1', 'url2'] 格式
        sources = json.loads(sources)
    
    # TODO: 实现多图批量处理
    # 注意: OpenAI gpt-4o 支持多图输入，但需要正确格式
    pass


def ai_query_batch(
    model_name: str,
    prompts: Union[List[str], str],
    schema_info: str = None
) -> str:
    """
    批量 SQL 查询生成
    
    一次性生成多条 SQL
    """
    if isinstance(prompts, str):
        prompts = json.loads(prompts)
    
    items = []
    for i, prompt in enumerate(prompts):
        items.append(f"问题{i+1}: {prompt}")
    
    prompt = f"""生成以下 SQL 查询:

{chr(10).join(items)}

{'表结构: ' + schema_info if schema_info else ''}

输出 JSON 数组:
[{{"index": 0, "sql": "SELECT ..."}}, {{"index": 1, "sql": "SELECT ..."}}, ...]"""

    result = call_model(model_name, prompt)
    # 解析 JSON...
```

### 4. SQL 函数

```sql
-- 批量过滤
CREATE OR REPLACE FUNCTION ai_filter_batch(
    model_name TEXT,
    condition TEXT,
    row_data_array JSONB
)
RETURNS JSONB
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.batch import ai_filter_batch
return ai_filter_batch(model_name, condition, row_data_array)
$$;

-- 批量图片描述
CREATE OR REPLACE FUNCTION ai_image_describe_batch(
    model_name TEXT,
    image_sources TEXT  -- JSON array string
)
RETURNS JSONB
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.batch import ai_image_describe_batch
return ai_image_describe_batch(model_name, image_sources)
$$;

-- 批量查询
CREATE OR REPLACE FUNCTION ai_query_batch(
    model_name TEXT,
    user_prompts TEXT,  -- JSON array string
    schema_info TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.batch import ai_query_batch
return ai_query_batch(model_name, user_prompts, schema_info)
$$;
```

### 5. 使用示例

```sql
-- 批量过滤
SELECT id, url, 
       (ai_filter_batch('gpt-4o', '金额大于1000', 
          jsonb_build_array(row_data->'金额')))->>'result' as matched
FROM (
  SELECT id, url, jsonb_build_object('金额', amount) as row_data
  FROM orders
) t;

-- 批量生成 SQL
SELECT * FROM jsonb_array_elements(
  ai_query_batch('gpt-4m', 
    '["获取所有用户", "统计订单数量"]',
    '表: users(id, name), orders(id, user_id, amount)'
  )
) ->> 'sql';
```

---

## 优化策略

### 1. 分批处理
- 单次 API 调用限制（如 OpenAI 最多 10 张图）
- 自动分批：`batch_size` 参数

### 2. 缓存层
- 基于 prompt hash 缓存结果
- TTL 策略（短期结果可缓存，长期结果不缓存）

### 3. 并发处理
- PostgreSQL 并行查询
- 异步调用 + 回调结果

### 4. 成本优化
- 批量比单条更便宜（共享 system prompt）
- 选择合适的模型（简单判断用小模型）

---

## 待实现文件

```
pg_semantic_operators/operators/batch.py  (新建)
sql/pg_semantic_operators--1.0.sql         (追加)
```