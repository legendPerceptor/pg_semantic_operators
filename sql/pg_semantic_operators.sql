-- pg_semantic_operators.sql
-- PostgreSQL 语义算子扩展

-- 检查 PL/Python 是否可用
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

-- ========== ai_filter ==========

CREATE OR REPLACE FUNCTION ai_filter(
    model_name TEXT,
    row_data JSONB
)
RETURNS BOOLEAN
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators import ai_filter
return ai_filter(model_name, row_data)
$$;

-- 便捷版本：接收 TEXT 并自动转换为 JSONB
CREATE OR REPLACE FUNCTION ai_filter(
    model_name TEXT,
    row_text TEXT
)
RETURNS BOOLEAN
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators import ai_filter
import json
try:
    row_json = json.loads(row_text)
except:
    row_json = row_text
return ai_filter(model_name, row_json)
$$;

-- ========== 元数据函数 ==========

CREATE OR REPLACE FUNCTION list_models()
RETURNS TEXT[]
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.config import list_models
return list_models()
$$;

COMMENT ON FUNCTION ai_query(TEXT, TEXT) IS 
'将自然语言转换为 SQL 查询。参数: model_name-模型名称, user_prompt-用户查询';
COMMENT ON FUNCTION ai_filter(TEXT, JSONB) IS 
'语义过滤判断。参数: model_name-模型名称, row_data-行数据(JSONB)';
COMMENT ON FUNCTION list_models() IS '列出所有可用模型';