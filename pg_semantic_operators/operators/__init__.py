"""Semantic operators for PostgreSQL"""

from .ai_filter import ai_filter, AI_FILTER_SYSTEM_PROMPT
from .ai_query import ai_query, AI_QUERY_SYSTEM_PROMPT_BASE
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
    "AI_FILTER_SYSTEM_PROMPT", "AI_QUERY_SYSTEM_PROMPT_BASE",
    # Batch operators
    "ai_filter_batch",
    "ai_image_filter_batch", 
    "ai_image_describe_batch",
    "ai_query_batch",
    "DEFAULT_BATCH_SIZE",
    "MAX_BATCH_SIZE"
]