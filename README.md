# pg_semantic_operators

PostgreSQL 语义算子扩展，提供基于 AI 的查询和过滤功能。

## 功能

### ai_query(model_name, user_prompt [, schema_info]) → text
将自然语言转换为 SQL 查询语句。

```sql
-- 简单用法
SELECT ai_query('gpt-4o', '找出最近一周的订单');

-- 带 schema 信息（推荐）
SELECT ai_query('gpt-4o', '找出最近一周的订单', get_schema_info());
```

### ai_filter(model_name, condition, row_data) → boolean
根据语义条件判断是否匹配，返回 true/false。

```sql
SELECT * FROM orders 
WHERE ai_filter('gpt-4o', '金额大于1000且状态是已完成', 
                jsonb_build_object('status', status, 'amount', amount));
```

### get_schema_info() → text
获取当前数据库 public schema 的表结构信息。

### list_models() → text[]
列出所有可用模型。

## 支持的模型

| 模型名 | Provider | 说明 |
|--------|----------|------|
| gpt-4o | OpenAI | OpenAI GPT-4o |
| claude-3-5-sonnet | Anthropic | Claude 3.5 Sonnet |
| minimax | Minimax | Minimax abab6.5s-chat |
| glm-4 | 智谱 | GLM-4-flash |
| qwen-coder | Ollama | 本地 Qwen 2.5 Coder |

## 快速开始 (Docker)

### 1. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

### 2. 启动容器

```bash
# 构建并启动
docker compose up -d --build

# 查看日志
docker compose logs -f
```

### 3. 连接数据库

```bash
# 方式一：进入容器
docker exec -it pg_semantic psql -U postgres -d semantic_test

# 方式二：本地连接
psql -h localhost -U postgres -d semantic_test
```

### 4. 运行测试

```bash
docker exec -it pg_semantic psql -U postgres -d semantic_test -f /docker-entrypoint-initdb.d/test.sql
```

## 本地安装

### 前置条件

1. PostgreSQL 16+
2. PL/Python3 扩展
3. Python 3.8+

### 安装步骤

```bash
# 1. 安装 Python 包
uv pip install -e .

# 2. 安装 SQL 扩展
make install

# 3. 在数据库中加载
psql -d your_database -f $(pg_config --sharedir)/extension/pg_semantic_operators.sql
```

## 使用示例

```sql
-- 创建测试表
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_name TEXT,
    amount NUMERIC,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO orders (customer_name, amount, status) VALUES
    ('张三', 500, '进行中'),
    ('李四', 1500, '已完成'),
    ('王五', 2000, '已完成');

-- 使用 ai_query 生成 SQL
SELECT ai_query('gpt-4o', '找出金额大于1000的订单', get_schema_info());

-- 使用 ai_filter 过滤数据
SELECT * FROM orders 
WHERE ai_filter('gpt-4o', '金额大于1000且状态是已完成', 
                jsonb_build_object('customer_name', customer_name, 'amount', amount, 'status', status));

-- 使用 GLM 模型
SELECT ai_query('glm-4', '找出最近一周的订单');

-- 使用 Minimax 模型
SELECT ai_filter('minimax', '金额大于1000', '{"金额": 1500}'::jsonb);
```

## 配置

### .env 文件

```env
# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key

# Minimax
MINIMAX_API_KEY=your-minimax-api-key

# 智谱 GLM
GLM_API_KEY=your-glm-api-key

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
```

### 环境变量

| 变量 | 说明 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API Key |
| `ANTHROPIC_API_KEY` | Anthropic API Key |
| `MINIMAX_API_KEY` | Minimax API Key |
| `GLM_API_KEY` | 智谱 GLM API Key |
| `OLLAMA_BASE_URL` | Ollama 地址 |
| `PG_SEMANTIC_CONFIG` | 自定义模型配置文件路径 |

### 自定义模型配置

创建 `/etc/pg_semantic/models.json`:

```json
{
  "my-gpt4": {
    "provider": "openai",
    "model": "gpt-4o",
    "api_key": "sk-xxx"
  },
  "my-minimax": {
    "provider": "minimax",
    "model": "abab6.5s-chat",
    "api_key": "xxx"
  },
  "my-glm": {
    "provider": "glm",
    "model": "glm-4-flash",
    "api_key": "xxx"
  }
}
```

## 目录结构

```
pg_semantic_operators/
├── pg_semantic_operators/          # Python 模块
│   ├── __init__.py
│   ├── config.py                   # 配置管理
│   ├── client.py                   # 模型调用客户端
│   └── operators.py                # 算子实现
├── sql/
│   ├── pg_semantic_operators.sql   # SQL 扩展定义
│   └── test.sql                    # 测试脚本
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── Makefile
└── README.md
```

## License

MIT
