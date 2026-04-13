"""Semantic operators for PostgreSQL"""

from .ai_filter import ai_filter, AI_FILTER_SYSTEM_PROMPT
from .ai_query import ai_query, AI_QUERY_SYSTEM_PROMPT
from .ai_query import (
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
from .ai_image import ai_image_filter, ai_image_describe
from .ai_audio import ai_audio_filter, ai_audio_describe
from .batch import (
    ai_filter_batch,
    ai_image_filter_batch,
    ai_image_describe_batch,
    ai_query_batch,
    DEFAULT_BATCH_SIZE,
    MAX_BATCH_SIZE
)

__all__ = [
    "ai_filter", "ai_query",
    "ai_image_filter", "ai_image_describe",
    "ai_audio_filter", "ai_audio_describe",
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
    # Batch operators
    "ai_filter_batch",
    "ai_image_filter_batch",
    "ai_image_describe_batch",
    "ai_query_batch",
    "DEFAULT_BATCH_SIZE",
    "MAX_BATCH_SIZE"
]
