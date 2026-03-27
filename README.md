# pg_semantic_operators

PostgreSQL 语义算子扩展，提供基于 AI 的查询和过滤功能。

## 算子

- `ai_query(text)` - 自然语言转 SQL 查询
- `ai_filter(jsonb)` - 语义条件过滤

## 安装

```bash
# 安装 PL/Python
CREATE EXTENSION plpython3u;

# 安装本扩展
make install
make installcheck
```

## 使用

```sql
-- 启用扩展
CREATE EXTENSION pg_semantic_operators;

-- 自然语言查询
SELECT * FROM ai_query('找出最近一周的订单');

-- 语义过滤
SELECT * FROM orders WHERE ai_filter(row_to_json(orders)::jsonb);
```