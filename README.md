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

## 测试

### 方式一：使用 Makefile 测试（推荐）

#### 1. 测试所有模型

运行完整的模型测试套件，包括配置检查、简单调用和完整功能测试：

```bash
# 确保已配置 .env 文件
make test-models
```

这个测试会：
- 列出所有可用模型
- 检查每个模型的配置（provider、model name、API key）
- 测试每个模型的简单响应
- 选择第一个可用模型进行完整的 `ai_filter` 和 `ai_query` 测试

#### 2. 快速测试单个模型

当只需要测试一个特定模型时：

```bash
# 测试 gpt-4o
make test-quick MODEL=gpt-4o

# 测试 glm-4
make test-quick MODEL=glm-4

# 测试 ollama 本地模型
make test-quick MODEL=qwen-coder
```

**示例输出：**

```
============================================================
快速测试模型: gpt-4o
============================================================

可用模型: ['gpt-4o', 'claude-3-5-sonnet', 'minimax', 'glm-4', 'qwen-coder']

--- 测试 1: 简单调用 ---
响应: Hello World

--- 测试 2: ai_filter ---
ai_filter('金额大于1000', {'金额': 1500}) = True

--- 测试 3: ai_query ---
生成的SQL: SELECT * FROM orders WHERE amount > 1000;
```

### 方式二：直接运行 Python 测试

#### 1. 运行完整测试套件

```bash
# 确保在项目根目录
cd /path/to/pg_semantic_operators

# 激活虚拟环境（如果使用）
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 运行测试
python tests/test_models.py
```

#### 2. 运行快速测试

```bash
# 测试特定模型
python tests/quick_test.py gpt-4o
python tests/quick_test.py glm-4
python tests/quick_test.py qwen-coder
```

### 方式三：在 PostgreSQL 中测试

#### 1. 安装扩展并连接数据库

```bash
# 使用 Docker
docker exec -it pg_semantic psql -U postgres -d semantic_test

# 或本地连接
psql -h localhost -U postgres -d semantic_test
```

#### 2. 运行测试脚本

```bash
# 在 psql 中
\i /docker-entrypoint-initdb.d/test.sql
```

#### 3. 手动测试

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

-- 1. 列出可用模型
SELECT list_models();

-- 2. 测试 ai_query
SELECT ai_query('gpt-4o', '找出金额大于1000的订单', get_schema_info());

-- 3. 测试 ai_filter
SELECT customer_name, amount, status
FROM orders
WHERE ai_filter('gpt-4o', '金额大于1000且状态是已完成',
                jsonb_build_object('customer_name', customer_name,
                                   'amount', amount,
                                   'status', status));

-- 4. 获取 schema 信息
SELECT get_schema_info();
```

### 测试故障排除

#### 问题 1: "No module named 'pg_semantic_operators'"

**原因：** Python 包未安装

**解决方案：**

```bash
# 使用 uv 安装
uv pip install -e .

# 或使用 pip
pip install -e .
```

#### 问题 2: "API key not configured"

**原因：** 环境变量未设置或 .env 文件不存在

**解决方案：**

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
nano .env  # 或使用其他编辑器
```

确保 `.env` 文件中包含对应模型的 API Key：

```env
# OpenAI
OPENAI_API_KEY=sk-your-actual-key-here

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here

# 智谱 GLM
GLM_API_KEY=your-glm-api-key-here

# Minimax
MINIMAX_API_KEY=your-minimax-api-key-here
```

#### 问题 3: "Connection error" 或 "Timeout"

**原因：** 网络问题或 API 服务不可用

**解决方案：**

```bash
# 检查网络连接
ping api.openai.com
ping open.bigmodel.cn

# 如果使用代理，确保环境变量已设置
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port

# 对于 Ollama 本地模型，确保 Ollama 服务正在运行
curl http://localhost:11434/api/tags
```

#### 问题 4: "Unknown provider" 或 "Model not found"

**原因：** 模型配置错误

**解决方案：**

```bash
# 检查 models.json 配置
cat models.json

# 或使用环境变量配置
cat .env

# 测试模型配置
python -c "from pg_semantic_operators.config import list_models; print(list_models())"
```

#### 问题 5: Ollama 模型测试失败

**原因：** Ollama 服务未运行或模型未下载

**解决方案：**

```bash
# 检查 Ollama 服务
curl http://localhost:11434/api/tags

# 启动 Ollama（如果未运行）
ollama serve

# 拉取模型
ollama pull qwen2.5-coder

# 测试连接
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder",
  "prompt": "Hello",
  "stream": false
}'
```

### 测试最佳实践

1. **先测试简单调用，再测试复杂功能**

   ```bash
   # 步骤 1: 测试模型是否可用
   python -c "from pg_semantic_operators import call_model; print(call_model('gpt-4o', 'Say OK'))"

   # 步骤 2: 测试 ai_filter
   python -c "from pg_semantic_operators import ai_filter; print(ai_filter('gpt-4o', '金额>1000', {'金额': 1500}))"

   # 步骤 3: 测试 ai_query
   python -c "from pg_semantic_operators import ai_query; print(ai_query('gpt-4o', '查询所有订单'))"
   ```

2. **使用低成本模型进行开发和测试**

   ```bash
   # 使用本地模型（免费）
   make test-quick MODEL=qwen-coder

   # 使用更便宜的云模型
   make test-quick MODEL=glm-4
   ```

3. **启用详细日志以调试**

   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)

   from pg_semantic_operators import call_model
   result = call_model('gpt-4o', 'test')
   ```

4. **在 PostgreSQL 中测试前，先在 Python 中测试**

   这样可以更快地发现和解决问题，避免 PostgreSQL 的复杂性。

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
