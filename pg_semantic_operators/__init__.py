"""
pg_semantic_operators - PostgreSQL 语义算子扩展
"""

from .operators import (
    ai_query, ai_filter, ai_image_filter, ai_image_describe,
    ai_audio_filter, ai_audio_describe,
    ai_filter_batch, ai_image_filter_batch, ai_image_describe_batch,
    ai_query_batch,
    DEFAULT_BATCH_SIZE, MAX_BATCH_SIZE,
    AI_FILTER_SYSTEM_PROMPT, AI_QUERY_SYSTEM_PROMPT,
    get_schema_info_enhanced,
    get_relevant_schema,
    get_schema_info_basic,
    build_prompt,
    extract_sql_from_response,
    OPERATOR_REGISTRY,
    validate_sql_syntax,
    self_correct,
    classify_error,
    security_check,
    ensure_limit,
    sanitize_sql,
)
from .config import get_model_config, list_models
from .client import call_model

__all__ = [
    "ai_query", "ai_filter",
    "ai_image_filter", "ai_image_describe",
    "ai_audio_filter", "ai_audio_describe",
    # Batch operators
    "ai_filter_batch",
    "ai_image_filter_batch",
    "ai_image_describe_batch",
    "ai_query_batch",
    "get_model_config", "list_models", "call_model",
    "AI_FILTER_SYSTEM_PROMPT", "AI_QUERY_SYSTEM_PROMPT",
    # ai_query sub-modules
    "get_schema_info_enhanced",
    "get_relevant_schema",
    "get_schema_info_basic",
    "build_prompt",
    "extract_sql_from_response",
    "OPERATOR_REGISTRY",
    "validate_sql_syntax",
    "self_correct",
    "classify_error",
    "security_check",
    "ensure_limit",
    "sanitize_sql",
    "DEFAULT_BATCH_SIZE", "MAX_BATCH_SIZE"
]
