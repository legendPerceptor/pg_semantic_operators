# pg_semantic_operators

PostgreSQL 语义算子扩展，提供基于 AI 的查询和过滤功能。

## 功能

### ai_query(model_name, user_prompt) → text
将自然语言转换为 SQL 查询语句。

```sql
SELECT ai_query('gpt-4o', '找出最近一周的订单');
-- 输出: SELECT * FROM orders WHERE created_at >= NOW() - INTERVAL '7 days'
```

### ai_filter(model_name, row_data) → boolean
根据语义条件判断是否匹配，返回 true/false。

```sql
SELECT * FROM orders 
WHERE ai_filter('gpt-4o', row_to_json(orders)::jsonb);
```

### list_models() → text[]
列出所有可用模型。

```sql
SELECT list_models();
```

## 支持的模型

| 模型名 | Provider | 说明 |
|--------|----------|------|
| gpt-4o | OpenAI | OpenAI GPT-4o |
| claude-3-5-sonnet | Anthropic | Claude 3.5 Sonnet |
| qwen-coder | Ollama | 本地 Qwen 2.5 Coder |

## 安装

### 前置条件

1. PostgreSQL 16+
2. PL/Python3 扩展
3. Python 依赖: `openai`, `anthropic`, `requests`

```bash
# 1. 安装 Python 依赖
pip install openai anthropic requests

# 2. 启用 PL/Python 扩展 (需要 superuser)
CREATE EXTENSION plpython3u;

# 3. 配置模型 (可选)
# 创建 /etc/pg_semantic/models.json:
# {
#   "gpt-4o": {
#     "provider": "openai",
#     "model": "gpt-4o",
#     "api_key": "your-key"
#   }
# }

# 4. 设置环境变量
export OPENAI_API_KEY="your-openai-key"
# 或
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### 安装扩展

```bash
# 方式一: 直接加载 SQL (开发模式)
psql -d your_database -f sql/pg_semantic_operators.sql

# 方式二: 安装到 PostgreSQL 系统 (生产)
cd /path/to/pg_semantic_operators
make install
```

## 使用示例

```sql
-- 启用扩展
CREATE EXTENSION plpython3u;
\i sql/pg_semantic_operators.sql

-- 测试 ai_query
SELECT ai_query('gpt-4o', '找出金额大于1000的订单');

-- 测试 ai_filter
CREATE TABLE orders AS SELECT * FROM (VALUES
  (1, '已完成', 1500),
  (2, '进行中', 800),
  (3, '已完成', 2000)
) AS t(id, status, amount);

SELECT * FROM orders 
WHERE ai_filter('gpt-4o', jsonb_build_object('status', status, 'amount', amount)) = true;
```

## 配置

### 环境变量

| 变量 | 说明 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API Key |
| `ANTHROPIC_API_KEY` | Anthropic API Key |
| `OLLAMA_BASE_URL` | Ollama 地址 (默认 http://localhost:11434) |
| `PG_SEMANTIC_CONFIG` | 自定义模型配置 JSON 文件路径 |

### 自定义模型配置

创建 `/etc/pg_semantic/models.json`:

```json
{
  "my-gpt4": {
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1"
  },
  "local-model": {
    "provider": "ollama",
    "model": "qwen2.5-coder:7b",
    "base_url": "http://localhost:11434"
  }
}
```

## 目录结构

```
pg_semantic_operators/
├── sql/
│   └── pg_semantic_operators.sql   # SQL 扩展定义
├── python/
│   ├── __init__.py                  # 包入口
│   ├── config.py                    # 模型配置
│   ├── client.py                    # 模型调用客户端
│   └── operators.py                 # 算子实现
├── test/                            # 测试用例
├── doc/                             # 文档
└── README.md
```

## License

MIT