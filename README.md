# pg_semantic_operators

[中文](docs/README_zh.md) | English

A PostgreSQL extension providing AI-powered query and filtering capabilities.

## Features

### ai_query(model_name, user_prompt [, schema_info]) → text

Converts natural language to SQL queries using a six-stage NL2SQL pipeline:

1. **Schema Linking** — Intelligently filters tables/columns relevant to the question
2. **Prompt Engineering** — Operator registry, few-shot examples, domain knowledge injection
3. **SQL Generation** — Calls LLM to generate SQL
4. **Validation & Self-Correction** — Syntax validation + LLM-based auto-correction (up to N retries)
5. **Candidate Selection** — Multi-candidate voting (reserved for future)
6. **Security Check** — SQL injection prevention, dangerous operation filtering, auto LIMIT

```sql
-- Simple usage
SELECT ai_query('minimax', 'Find orders from the past week');

-- With schema info (recommended)
SELECT ai_query('minimax', 'Find orders from the past week', get_schema_info());

-- With enhanced parameters
SELECT ai_query('minimax', 'Find high-value orders', get_schema_info_enhanced(),
    auto_correct := true,
    max_retries := 2,
    read_only := true,
    max_limit := 1000
);
```

### ai_filter(model_name, condition, row_data) → boolean

Evaluates whether a row matches a semantic condition, returns true/false.

```sql
SELECT * FROM orders
WHERE ai_filter('minimax', 'amount greater than 1000 and status is completed',
                jsonb_build_object('status', status, 'amount', amount));
```

### ai_image_filter(model_name, image_source, description) → boolean

Determines whether an image matches a description, returns true/false. `image_source` can be a URL or local file path.

```sql
-- From URL
SELECT ai_image_filter('gpt-4o', 'https://example.com/image.jpg', 'product photo');

-- From local file
SELECT ai_image_filter('gpt-4o', '/path/to/image.jpg', 'contains a cat');
```

### ai_image_describe(model_name, image_source) → text

Generates a natural language description of an image. `image_source` can be a URL or local file path.

```sql
SELECT ai_image_describe('gpt-4o', 'https://example.com/image.jpg');
SELECT ai_image_describe('gpt-4o', '/path/to/image.jpg');
```

### ai_audio_filter(model_name, audio_source, description) → boolean

Determines whether an audio clip matches a description, returns true/false. `audio_source` can be a URL or local file path.

```sql
-- Check if audio is in Chinese
SELECT ai_audio_filter('gpt-4o-audio-preview', '/path/to/audio.mp3', 'Chinese');

-- Check if audio contains a specific topic
SELECT ai_audio_filter('gpt-4o-audio-preview', 'https://example.com/audio.mp3', 'weather forecast');
```

### ai_audio_describe(model_name, audio_source) → text

Generates a natural language description of an audio clip, including language, speaker count, topic, etc. `audio_source` can be a URL or local file path.

```sql
SELECT ai_audio_describe('gpt-4o-audio-preview', '/path/to/audio.mp3');
SELECT ai_audio_describe('gpt-4o-audio-preview', 'https://example.com/audio.mp3');
```

## Batch Operators

Batch operators process multiple items in a single or concurrent API call, significantly improving efficiency.

### ai_filter_batch(model_name, condition, row_data_array [, batch_size]) → jsonb

Batch semantic filtering, processing multiple rows in a single API call.

```sql
-- Batch filter orders
SELECT * FROM jsonb_to_recordset(
  ai_filter_batch('gpt-4o', 'amount greater than 1000',
    '[{"amount": 1500}, {"amount": 500}, {"amount": 2000}]'::jsonb)
) AS t(id int, result boolean);

-- With table data
SELECT t.*, r.result
FROM orders t,
  jsonb_to_recordset(
    ai_filter_batch('minimax', 'high-value orders',
      (SELECT jsonb_agg(row_to_json(t)::jsonb) FROM (
        SELECT id, customer_name, amount, status FROM orders LIMIT 20
      ) t))
  ) AS r(id int, result boolean)
WHERE t.id = r.id AND r.result = true;
```

### ai_image_filter_batch(model_name, image_sources, description [, batch_size]) → jsonb

Batch image filtering using concurrent processing for higher throughput.

```sql
SELECT * FROM jsonb_to_recordset(
  ai_image_filter_batch('gpt-4o',
    '["https://example.com/img1.jpg", "https://example.com/img2.jpg"]'::jsonb,
    'contains a cat')
) AS t(index int, result boolean);
```

### ai_image_describe_batch(model_name, image_sources [, batch_size]) → jsonb

Batch image description using concurrent processing.

```sql
SELECT * FROM jsonb_to_recordset(
  ai_image_describe_batch('gpt-4o',
    '["https://example.com/img1.jpg", "https://example.com/img2.jpg"]'::jsonb)
) AS t(index int, description text);
```

### ai_query_batch(model_name, user_prompts [, schema_info, batch_size]) → jsonb

Batch SQL query generation, generating multiple SQL statements in a single API call.

```sql
SELECT * FROM jsonb_to_recordset(
  ai_query_batch('minimax',
    '["Query all users", "Count total orders", "Find the highest amount order"]'::jsonb,
    get_schema_info())
) AS t(index int, sql text);
```

### Batch Size Limits

| Operator | Default Batch Size | Max Batch Size | Description |
|----------|--------------------|----------------|-------------|
| ai_filter_batch | 10 | 20 | Single API call processing |
| ai_image_filter_batch | 10 | 10 | Concurrent processing (OpenAI limit) |
| ai_image_describe_batch | 10 | 10 | Concurrent processing (OpenAI limit) |
| ai_query_batch | 10 | 20 | Single API call processing |

### get_schema_info() → text

Retrieves the table structure information for the `public` schema of the current database.

### get_schema_info_enhanced() → text

Retrieves enhanced schema information in DDL `CREATE TABLE` format, including primary keys, foreign keys, column comments, and example values.

### get_relevant_schema(model_name, question) → text

Intelligently filters tables relevant to the question using LLM, returning a concise schema description.

### list_models() → text[]

Lists all available models.

## Supported Models

| Model | Provider | Description | Image Support | Audio Support |
|-------|----------|-------------|---------------|---------------|
| gpt-4o | OpenAI | OpenAI GPT-4o | Yes | No |
| gpt-4o-audio-preview | OpenAI | OpenAI GPT-4o Audio | No | Yes |
| claude-3-5-sonnet | Anthropic | Claude 3.5 Sonnet | Yes | No |
| minimax | Minimax | Minimax abab6.5s-chat | No | No |
| glm-4 | Zhipu | GLM-4-flash | No | No |
| qwen-coder | Ollama | Local Qwen 2.5 Coder | No | No |

Models are automatically enabled based on the API keys configured in your `.env` file.

## Quick Start (Docker)

### 1. Configure API Key

```bash
cp .env.example .env
# Edit .env file and fill in your API keys
```

### 2. Start Container

```bash
# Build and start
docker compose up -d --build

# Install the pg_semantic_operators extension (requires CASCADE for plpython3u dependency)
docker exec pg_semantic psql -U postgres -d semantic_test -c "CREATE EXTENSION pg_semantic_operators CASCADE;"

# View logs
docker compose logs -f
```

### 3. Connect to Database

```bash
# Enter psql
docker exec -it pg_semantic psql -U postgres -d semantic_test
```

### 4. Quick Test

```bash
# Test minimax model
docker exec pg_semantic psql -U postgres -d semantic_test -c "SELECT ai_filter('minimax', 'amount greater than 100', '{\"amount\": 150}'::jsonb);"
```

### 5. Run Full Tests

Test basic multimodal operator functionality.

```bash
docker cp sql/test.sql pg_semantic:/tmp/test.sql
docker exec pg_semantic psql -U postgres -d semantic_test -f /tmp/test.sql
```

Test batch operators.

```bash
docker cp sql/test_batch.sql pg_semantic:/tmp/test_batch.sql
docker exec pg_semantic psql -U postgres -d semantic_test -f /tmp/test_batch.sql
```

## Docker Proxy Configuration

If you encounter network issues, check the proxy settings in `~/.docker/config.json`. Add API domains to `noProxy`:

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

Rebuild the container after modification:
```bash
docker compose down && docker compose up -d --build
```

## Local Installation

### Prerequisites

1. PostgreSQL 18+ (or 16+)
2. PL/Python3 extension
3. Python 3.8+

### Installation Steps

```bash
# 1. Install Python package
pip install -e .

# 2. Install SQL extension
make install

# 3. Load in database
psql -d your_database -f $(pg_config --sharedir)/extension/pg_semantic_operators--1.0.sql
```

## Usage Examples

```sql
-- Create test table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_name TEXT,
    amount NUMERIC,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO orders (customer_name, amount, status) VALUES
    ('Alice', 500, 'in progress'),
    ('Bob', 1500, 'completed'),
    ('Charlie', 2000, 'completed');

-- List available models
SELECT list_models();

-- Generate SQL using ai_query
SELECT ai_query('minimax', 'Find orders with amount greater than 1000', get_schema_info());

-- Filter data using ai_filter
SELECT * FROM orders
WHERE ai_filter('minimax', 'amount greater than 1000 and status is completed',
                jsonb_build_object('customer_name', customer_name, 'amount', amount, 'status', status));

-- Get schema info
SELECT get_schema_info();

-- Describe an image
SELECT ai_image_describe('gpt-4o', 'https://httpbin.org/image/png');

-- Filter images
SELECT * FROM products
WHERE ai_image_filter('gpt-4o', image_url, 'pink cartoon pig face');

-- Describe audio
SELECT ai_audio_describe('gpt-4o-audio-preview', '/path/to/audio.mp3');

-- Filter audio
SELECT * FROM audio_records
WHERE ai_audio_filter('gpt-4o-audio-preview', audio_url, 'Chinese');
```

## Testing (Python)

### Test All Models

```bash
make test-models
```

### Quick Test Single Model

```bash
make quick_test MODEL=minimax
make quick_test MODEL=glm-4
```

### Unit Tests

```bash
uv run --extra dev pytest tests/test_ai_query/ -v
```

## Configuration

### .env File

```env
# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key

# Minimax
MINIMAX_API_KEY=your-minimax-api-key
MINIMAX_BASE_URL=https://api.minimaxi.com/anthropic

# Zhipu GLM
GLM_API_KEY=your-glm-api-key

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API Key |
| `ANTHROPIC_API_KEY` | Anthropic API Key |
| `MINIMAX_API_KEY` | Minimax API Key |
| `GLM_API_KEY` | Zhipu GLM API Key |
| `OLLAMA_BASE_URL` | Ollama server address |
| `PG_SEMANTIC_CONFIG` | Custom model configuration file path |

## Troubleshooting

### "No module named 'pg_semantic_operators'"

The Python package is not installed. Fix:

```bash
pip install -e . --break-system-packages
```

### "Connection error"

Check:
1. API keys are configured correctly
2. Docker proxy settings are correct
3. Network connection is working

### Ollama Model Test Failure

Make sure the Ollama service is running:

```bash
ollama serve
ollama pull qwen2.5-coder
```

## Project Structure

```
pg_semantic_operators/
├── pg_semantic_operators/              # Python module
│   ├── __init__.py
│   ├── config.py                      # Configuration management
│   ├── client.py                      # Model call client
│   └── operators/                     # Operator sub-modules
│       ├── ai_filter.py               # Semantic filtering
│       ├── ai_query/                  # NL2SQL six-stage pipeline
│       │   ├── __init__.py
│       │   ├── core.py                # Main entry point
│       │   ├── schema_linking.py      # Schema linking
│       │   ├── prompt_builder.py      # Prompt construction
│       │   ├── validator.py           # SQL validation & self-correction
│       │   └── security.py            # Security checks
│       ├── ai_image.py                # Image operators
│       ├── ai_audio.py                # Audio operators
│       └── batch.py                   # Batch operators
├── tests/
│   └── test_ai_query/                 # ai_query unit tests (133 tests)
├── sql/
│   ├── pg_semantic_operators--1.0.sql # SQL extension definition
│   └── test.sql                       # Test scripts
├── docs/
│   ├── ai_query_improvement_plan.md   # ai_query improvement plan
│   └── README_zh.md                   # Chinese documentation
├── pg_semantic_operators.control       # PostgreSQL extension control file
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## License

MIT
