-- pg_semantic_operators.sql
-- PostgreSQL 语义算子扩展

CREATE EXTENSION IF NOT EXISTS plpython3u;

-- ========== ai_query ==========

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

-- ========== 辅助函数 ==========

CREATE OR REPLACE FUNCTION get_schema_info()
RETURNS TEXT
LANGUAGE plpython3u
AS $$
import json
query = """
SELECT 
    t.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable
FROM information_schema.tables t
JOIN information_schema.columns c ON t.table_name = c.table_name
WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
ORDER BY t.table_name, c.ordinal_position;
"""
try:
    result = plpy.execute(query)
    tables = {}
    for row in result:
        table_name = row['table_name']
        if table_name not in tables:
            tables[table_name] = []
        tables[table_name].append({
            'column': row['column_name'],
            'type': row['data_type'],
            'nullable': row['is_nullable']
        })
    
    output = []
    for table_name, columns in tables.items():
        output.append(f"表: {table_name}")
        for col in columns:
            nullable = "NULL" if col['nullable'] == 'YES' else "NOT NULL"
            output.append(f"  - {col['column']} ({col['type']}) {nullable}")
        output.append("")
    
    return "\n".join(output)
except Exception as e:
    return f"无法获取schema信息: {str(e)}"
$$;

CREATE OR REPLACE FUNCTION list_models()
RETURNS TEXT[]
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.config import list_models
return list_models()
$$;

-- ========== 注释 ==========

COMMENT ON FUNCTION ai_query(TEXT, TEXT) IS 
'将自然语言转换为 SQL 查询。参数: model_name-模型名称, user_prompt-用户查询';
COMMENT ON FUNCTION ai_query(TEXT, TEXT, TEXT) IS 
'将自然语言转换为 SQL 查询（带schema信息）。参数: model_name-模型名称, user_prompt-用户查询, schema_info-数据库结构信息';
COMMENT ON FUNCTION ai_filter(TEXT, TEXT, JSONB) IS 
'语义过滤判断。参数: model_name-模型名称, condition-过滤条件, row_data-行数据(JSONB)';
COMMENT ON FUNCTION ai_filter(TEXT, TEXT, TEXT) IS 
'语义过滤判断。参数: model_name-模型名称, condition-过滤条件, row_text-行数据(JSON文本)';
COMMENT ON FUNCTION get_schema_info() IS 
'获取当前数据库public schema的表结构信息';
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
