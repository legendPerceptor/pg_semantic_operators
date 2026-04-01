# pg_semantic_operators

PostgreSQL 语义算子扩展，提供基于 AI 的查询和过滤功能。

## 功能

### ai_query(model_name, user_prompt [, schema_info]) → text
将自然语言转换为 SQL 查询语句。

```sql
-- 简单用法
SELECT ai_query('minimax', '找出最近一周的订单');

-- 带 schema 信息（推荐）
SELECT ai_query('minimax', '找出最近一周的订单', get_schema_info());
```

### ai_filter(model_name, condition, row_data) → boolean
根据语义条件判断是否匹配，返回 true/false。

```sql
SELECT * FROM orders
WHERE ai_filter('minimax', '金额大于1000且状态是已完成',
                jsonb_build_object('status', status, 'amount', amount));
```

### ai_image_filter(model_name, image_source, description) → boolean
根据描述判断图片是否符合条件，返回 true/false。image_source 可以是 URL 或本地文件路径。

```sql
-- 判断网络图片
SELECT ai_image_filter('gpt-4o', 'https://example.com/image.jpg', '产品照片');

-- 判断本地图片
SELECT ai_image_filter('gpt-4o', '/path/to/image.jpg', '包含猫');
```

### ai_image_describe(model_name, image_source) → text
生成图片的自然语言描述。image_source 可以是 URL 或本地文件路径。

```sql
-- 描述网络图片
SELECT ai_image_describe('gpt-4o', 'https://example.com/image.jpg');

-- 描述本地图片
SELECT ai_image_describe('gpt-4o', '/path/to/image.jpg');
```

### ai_audio_filter(model_name, audio_source, description) → boolean
根据描述判断音频是否符合条件，返回 true/false。audio_source 可以是 URL 或本地文件路径。

```sql
-- 判断音频是否为中文
SELECT ai_audio_filter('gpt-4o-audio-preview', '/path/to/audio.mp3', '中文');

-- 判断音频是否包含特定主题
SELECT ai_audio_filter('gpt-4o-audio-preview', 'https://example.com/audio.mp3', '包含天气预报');
```

### ai_audio_describe(model_name, audio_source) → text
生成音频的自然语言描述，包括语言、说话人数量、主题等。audio_source 可以是 URL 或本地文件路径。

```sql
-- 描述本地音频
SELECT ai_audio_describe('gpt-4o-audio-preview', '/path/to/audio.mp3');

-- 描述网络音频
SELECT ai_audio_describe('gpt-4o-audio-preview', 'https://example.com/audio.mp3');
```

### get_schema_info() → text
获取当前数据库 public schema 的表结构信息。

### list_models() → text[]
列出所有可用模型。

## 支持的模型

| 模型名 | Provider | 说明 | 支持图片 | 支持音频 |
|--------|----------|------|---------|---------|
| gpt-4o | OpenAI | OpenAI GPT-4o | ✅ | ❌ |
| gpt-4o-audio-preview | OpenAI | OpenAI GPT-4o Audio | ❌ | ✅ |
| claude-3-5-sonnet | Anthropic | Claude 3.5 Sonnet | ✅ | ❌ |
| minimax | Minimax | Minimax abab6.5s-chat | ❌ | ❌ |
| glm-4 | 智谱 | GLM-4-flash | ❌ | ❌ |
| qwen-coder | Ollama | 本地 Qwen 2.5 Coder | ❌ | ❌ |

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

# 安装pg_semantic_operators插件，它依赖plpython3u所以需要CASCADE来安装前置插件
docker exec pg_semantic psql -U postgres -d semantic_test -c "CREATE EXTENSION pg_semantic_operators CASCADE;"

# 查看日志
docker compose logs -f
```

### 3. 连接数据库

```bash
# 进入 psql
docker exec -it pg_semantic psql -U postgres -d semantic_test
```

### 4. 快速测试

```bash
# 测试 minimax 模型
docker exec pg_semantic psql -U postgres -d semantic_test -c "SELECT ai_filter('minimax', '金额大于100', '{\"金额\": 150}'::jsonb);"
```

### 5. 运行完整测试

```bash
# 将测试脚本复制到容器并运行
docker cp sql/test.sql pg_semantic:/tmp/test.sql
docker exec pg_semantic psql -U postgres -d semantic_test -f /tmp/test.sql
```

## Docker 代理配置

如果遇到网络问题，检查 `~/.docker/config.json` 中的代理设置。将 API 域名添加到 `noProxy`:

```json
{
  "proxies": {
    "default": {
      "httpProxy": "http://127.0.0.1:1087",
      "httpsProxy": "http://127.0.0.1:1087",
      "noProxy": "localhost,127.0.0.1,api.minimaxi.com,api.openai.com,api.anthropic.com,open.bigmodel.cn"
    }
  }
}
```

修改后需要重建容器：
```bash
docker compose down && docker compose up -d --build
```

## 本地安装

### 前置条件

1. PostgreSQL 18+ (或 16+)
2. PL/Python3 扩展
3. Python 3.8+

### 安装步骤

```bash
# 1. 安装 Python 包
pip install -e .

# 2. 安装 SQL 扩展
make install

# 3. 在数据库中加载
psql -d your_database -f $(pg_config --sharedir)/extension/pg_semantic_operators--1.0.sql
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

-- 列出可用模型
SELECT list_models();

-- 使用 ai_query 生成 SQL
SELECT ai_query('minimax', '找出金额大于1000的订单', get_schema_info());

-- 使用 ai_filter 过滤数据
SELECT * FROM orders
WHERE ai_filter('minimax', '金额大于1000且状态是已完成',
                jsonb_build_object('customer_name', customer_name, 'amount', amount, 'status', status));

-- 获取 schema 信息
SELECT get_schema_info();

-- 使用 ai_image_describe 描述图片
SELECT ai_image_describe('gpt-4o', 'https://httpbin.org/image/png');

-- 使用 ai_image_filter 过滤图片
SELECT * FROM products
WHERE ai_image_filter('gpt-4o', image_url, '粉色的卡通猪脸');

-- 使用 ai_audio_describe 描述音频
SELECT ai_audio_describe('gpt-4o-audio-preview', '/path/to/audio.mp3');

-- 使用 ai_audio_filter 过滤音频
SELECT * FROM audio_records
WHERE ai_audio_filter('gpt-4o-audio-preview', audio_url, '中文');
```

## 测试 (Python)

### 测试所有模型

```bash
make test-models
```

### 快速测试单个模型

```bash
make quick_test MODEL=minimax
make quick_test MODEL=glm-4
```

## 配置

### .env 文件

```env
# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key

# Minimax
MINIMAX_API_KEY=your-minimax-api-key
MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic

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

## 故障排除

### "No module named 'pg_semantic_operators'"

Python 包未安装。解决方案：

```bash
pip install -e . --break-system-packages
```

### "Connection error"

检查：
1. API Key 是否配置正确
2. Docker 代理设置是否正确
3. 网络连接是否正常

### Ollama 模型测试失败

确保 Ollama 服务正在运行：

```bash
ollama serve
ollama pull qwen2.5-coder
```

## 目录结构

```
pg_semantic_operators/
├── pg_semantic_operators/              # Python 模块
│   ├── __init__.py
│   ├── config.py                      # 配置管理
│   ├── client.py                      # 模型调用客户端
│   ├── operators.py                   # 算子实现
│   └── operators/                     # 算子子模块
├── sql/
│   ├── pg_semantic_operators--1.0.sql # SQL 扩展定义
│   └── test.sql                       # 测试脚本
├── pg_semantic_operators.control       # PostgreSQL 扩展控制文件
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## License

MIT