-- pg_semantic_operators.sql
-- PostgreSQL 语义算子扩展

CREATE EXTENSION IF NOT EXISTS plpython3u;

-- ========== ai_query (增强版 NL2SQL) ==========

CREATE OR REPLACE FUNCTION ai_query(
    model_name TEXT,
    user_prompt TEXT
)
RETURNS TEXT
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators import ai_query
return ai_query(model_name, user_prompt)
$$;

CREATE OR REPLACE FUNCTION ai_query(
    model_name TEXT,
    user_prompt TEXT,
    schema_info TEXT
)
RETURNS TEXT
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators import ai_query
return ai_query(model_name, user_prompt, schema_info)
$$;

-- ========== ai_filter ==========

CREATE OR REPLACE FUNCTION ai_filter(
    model_name TEXT,
    condition TEXT,
    row_data JSONB
)
RETURNS BOOLEAN
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators import ai_filter
return ai_filter(model_name, condition, row_data)
$$;

CREATE OR REPLACE FUNCTION ai_filter(
    model_name TEXT,
    condition TEXT,
    row_text TEXT
)
RETURNS BOOLEAN
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators import ai_filter
return ai_filter(model_name, condition, row_text)
$$;

-- ========== 辅助函数：Schema 信息 ==========

CREATE OR REPLACE FUNCTION get_schema_info()
RETURNS TEXT
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.ai_query.schema_linking import get_schema_info_basic
return get_schema_info_basic(plpy)
$$;

CREATE OR REPLACE FUNCTION get_schema_info_enhanced(
    include_examples BOOLEAN DEFAULT TRUE,
    include_foreign_keys BOOLEAN DEFAULT TRUE
)
RETURNS TEXT
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.ai_query.schema_linking import get_schema_info_enhanced
return get_schema_info_enhanced(plpy, include_examples=include_examples, include_foreign_keys=include_foreign_keys)
$$;

CREATE OR REPLACE FUNCTION get_relevant_schema(
    model_name TEXT,
    question TEXT
)
RETURNS TEXT
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.ai_query.schema_linking import get_relevant_schema
from pg_semantic_operators.client import call_model
return get_relevant_schema(plpy, model_name, question, call_model_fn=call_model)
$$;

-- ========== 辅助函数：SQL 安全检查 ==========

CREATE OR REPLACE FUNCTION ai_query_security_check(
    sql TEXT,
    read_only BOOLEAN DEFAULT TRUE
)
RETURNS TEXT
LANGUAGE plpython3u
AS $$
import json
from pg_semantic_operators.operators.ai_query.security import security_check
is_safe, error_msg = security_check(sql, read_only=read_only)
return json.dumps({"is_safe": is_safe, "error_message": error_msg}, ensure_ascii=False)
$$;

-- ========== 辅助函数：SQL 验证 ==========

CREATE OR REPLACE FUNCTION ai_query_validate(
    sql TEXT
)
RETURNS TEXT
LANGUAGE plpython3u
AS $$
import json
from pg_semantic_operators.operators.ai_query.validator import validate_sql_syntax
is_valid, error_msg = validate_sql_syntax(sql)
return json.dumps({"is_valid": is_valid, "error_message": error_msg}, ensure_ascii=False)
$$;

-- ========== Few-shot 示例管理 ==========

CREATE TABLE IF NOT EXISTS ai_query_examples (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION ai_query_add_example(
    question TEXT,
    sql_query TEXT,
    description TEXT DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpython3u
AS $$
plpy.execute(
    "INSERT INTO ai_query_examples (question, sql_query, description) VALUES ($1, $2, $3)",
    [question, sql_query, description]
)
$$;

CREATE OR REPLACE FUNCTION ai_query_list_examples()
RETURNS TABLE(id INTEGER, question TEXT, sql_query TEXT, description TEXT)
LANGUAGE plpython3u
AS $$
result = plpy.execute("SELECT id, question, sql_query, description FROM ai_query_examples ORDER BY id")
return [{"id": r["id"], "question": r["question"], "sql_query": r["sql_query"], "description": r["description"]} for r in result]
$$;

-- ========== 领域知识管理 ==========

CREATE TABLE IF NOT EXISTS ai_query_knowledge (
    id SERIAL PRIMARY KEY,
    term TEXT UNIQUE NOT NULL,
    definition TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION ai_query_add_knowledge(
    term TEXT,
    definition TEXT
)
RETURNS VOID
LANGUAGE plpython3u
AS $$
plpy.execute(
    "INSERT INTO ai_query_knowledge (term, definition) VALUES ($1, $2) ON CONFLICT (term) DO UPDATE SET definition = EXCLUDED.definition",
    [term, definition]
)
$$;

CREATE OR REPLACE FUNCTION ai_query_list_knowledge()
RETURNS TABLE(id INTEGER, term TEXT, definition TEXT)
LANGUAGE plpython3u
AS $$
result = plpy.execute("SELECT id, term, definition FROM ai_query_knowledge ORDER BY id")
return [{"id": r["id"], "term": r["term"], "definition": r["definition"]} for r in result]
$$;

-- ========== 模型列表 ==========

CREATE OR REPLACE FUNCTION list_models()
RETURNS TEXT[]
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.config import list_models
return list_models()
$$;

-- ========== 注释 ==========

COMMENT ON FUNCTION ai_query(TEXT, TEXT) IS 
'将自然语言转换为 SQL 查询（增强版，含安全检查和自修正）。参数: model_name-模型名称, user_prompt-用户查询';
COMMENT ON FUNCTION ai_query(TEXT, TEXT, TEXT) IS 
'将自然语言转换为 SQL 查询（增强版，含安全检查和自修正）。参数: model_name-模型名称, user_prompt-用户查询, schema_info-数据库结构信息';
COMMENT ON FUNCTION ai_filter(TEXT, TEXT, JSONB) IS 
'语义过滤判断。参数: model_name-模型名称, condition-过滤条件, row_data-行数据(JSONB)';
COMMENT ON FUNCTION ai_filter(TEXT, TEXT, TEXT) IS 
'语义过滤判断。参数: model_name-模型名称, condition-过滤条件, row_text-行数据(JSON文本)';
COMMENT ON FUNCTION get_schema_info() IS 
'获取当前数据库public schema的表结构信息（基础版，纯文本格式）';
COMMENT ON FUNCTION get_schema_info_enhanced(BOOLEAN, BOOLEAN) IS 
'获取增强版数据库表结构信息（DDL格式，含外键、注释、示例值）。参数: include_examples-是否包含示例值, include_foreign_keys-是否包含外键关系';
COMMENT ON FUNCTION get_relevant_schema(TEXT, TEXT) IS 
'基于用户问题智能筛选相关的数据库表结构。参数: model_name-模型名称, question-用户自然语言问题';
COMMENT ON FUNCTION ai_query_security_check(TEXT, BOOLEAN) IS 
'检查SQL语句安全性。参数: sql-SQL语句, read_only-是否只允许SELECT查询';
COMMENT ON FUNCTION ai_query_validate(TEXT) IS 
'验证SQL语句语法。参数: sql-SQL语句';
COMMENT ON FUNCTION ai_query_add_example(TEXT, TEXT, TEXT) IS 
'添加NL2SQL few-shot示例。参数: question-自然语言问题, sql_query-SQL查询, description-描述(可选)';
COMMENT ON FUNCTION ai_query_list_examples() IS 
'列出所有NL2SQL few-shot示例';
COMMENT ON FUNCTION ai_query_add_knowledge(TEXT, TEXT) IS 
'添加业务领域知识（术语映射）。参数: term-术语, definition-定义/映射';
COMMENT ON FUNCTION ai_query_list_knowledge() IS 
'列出所有业务领域知识';
COMMENT ON FUNCTION list_models() IS '列出所有可用模型';

-- ========== ai_image_filter ==========

CREATE OR REPLACE FUNCTION ai_image_filter(
    model_name TEXT,
    image_source TEXT,
    description TEXT
)
RETURNS BOOLEAN
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.ai_image import ai_image_filter
return ai_image_filter(model_name, image_source, description)
$$;

-- ========== ai_image_describe ==========

CREATE OR REPLACE FUNCTION ai_image_describe(
    model_name TEXT,
    image_source TEXT
)
RETURNS TEXT
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.ai_image import ai_image_describe
return ai_image_describe(model_name, image_source)
$$;

-- ========== ai_audio_filter ==========

CREATE OR REPLACE FUNCTION ai_audio_filter(
    model_name TEXT,
    audio_source TEXT,
    description TEXT
)
RETURNS BOOLEAN
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.ai_audio import ai_audio_filter
return ai_audio_filter(model_name, audio_source, description)
$$;

-- ========== ai_audio_describe ==========

CREATE OR REPLACE FUNCTION ai_audio_describe(
    model_name TEXT,
    audio_source TEXT
)
RETURNS TEXT
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.ai_audio import ai_audio_describe
return ai_audio_describe(model_name, audio_source)
$$;

-- ========== 注释 ==========

COMMENT ON FUNCTION ai_image_filter(TEXT, TEXT, TEXT) IS
'判断图片是否符合描述。参数: model_name-模型名称, image_source-图片URL或本地路径, description-描述文本';
COMMENT ON FUNCTION ai_image_describe(TEXT, TEXT) IS
'生成图片描述。参数: model_name-模型名称, image_source-图片URL或本地路径';

-- ========== ai_filter_batch ==========

CREATE OR REPLACE FUNCTION ai_filter_batch(
    model_name TEXT,
    condition TEXT,
    row_data_array JSONB,
    batch_size INTEGER DEFAULT 10
)
RETURNS JSONB
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.batch import ai_filter_batch
result = ai_filter_batch(model_name, condition, row_data_array, batch_size)
return result
$$;

-- ========== ai_image_filter_batch ==========

CREATE OR REPLACE FUNCTION ai_image_filter_batch(
    model_name TEXT,
    image_sources JSONB,
    description TEXT,
    batch_size INTEGER DEFAULT 10
)
RETURNS JSONB
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.batch import ai_image_filter_batch
result = ai_image_filter_batch(model_name, image_sources, description, batch_size)
return result
$$;

-- ========== ai_image_describe_batch ==========

CREATE OR REPLACE FUNCTION ai_image_describe_batch(
    model_name TEXT,
    image_sources JSONB,
    batch_size INTEGER DEFAULT 10
)
RETURNS JSONB
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.batch import ai_image_describe_batch
result = ai_image_describe_batch(model_name, image_sources, batch_size)
return result
$$;

-- ========== ai_query_batch ==========

CREATE OR REPLACE FUNCTION ai_query_batch(
    model_name TEXT,
    user_prompts JSONB,
    schema_info TEXT DEFAULT NULL,
    batch_size INTEGER DEFAULT 10
)
RETURNS JSONB
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.batch import ai_query_batch
result = ai_query_batch(model_name, user_prompts, schema_info, batch_size)
return result
$$;

-- ========== 注释 ==========

COMMENT ON FUNCTION ai_filter_batch(TEXT, TEXT, JSONB, INTEGER) IS
'批量语义过滤。参数: model_name-模型名称, condition-过滤条件, row_data_array-行数据数组(JSONB), batch_size-批大小(默认10)';
COMMENT ON FUNCTION ai_image_filter_batch(TEXT, JSONB, TEXT, INTEGER) IS
'批量图片过滤。参数: model_name-模型名称, image_sources-图片URL数组(JSONB), description-描述文本, batch_size-批大小(默认10)';
COMMENT ON FUNCTION ai_image_describe_batch(TEXT, JSONB, INTEGER) IS
'批量图片描述。参数: model_name-模型名称, image_sources-图片URL数组(JSONB), batch_size-批大小(默认10)';
COMMENT ON FUNCTION ai_query_batch(TEXT, JSONB, TEXT, INTEGER) IS
'批量SQL查询生成。参数: model_name-模型名称, user_prompts-用户查询数组(JSONB), schema_info-数据库结构, batch_size-批大小(默认10)';
