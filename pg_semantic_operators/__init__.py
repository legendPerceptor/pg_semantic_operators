"""
pg_semantic_operators - PostgreSQL 语义算子扩展
"""

from .operators import ai_query, ai_filter
from .config import get_model_config, list_models
from .client import call_model

# New: export prompts for testing
from .operators.ai_filter import AI_FILTER_SYSTEM_PROMPT
from .operators.ai_query import AI_QUERY_SYSTEM_PROMPT_BASE

__all__ = [
    "ai_query", "ai_filter",
    "get_model_config", "list_models", "call_model",
    "AI_FILTER_SYSTEM_PROMPT", "AI_QUERY_SYSTEM_PROMPT_BASE"  # New exports
]
