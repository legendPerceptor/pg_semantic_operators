# Backward compatibility shim - imports from new modular structure
# This file is deprecated. Use: from pg_semantic_operators import ai_filter, ai_query, ai_image_filter, ai_image_describe

import warnings

from .operators.ai_filter import ai_filter
from .operators.ai_query import ai_query
from .operators.ai_image import ai_image_filter, ai_image_describe

warnings.warn(
    "Direct import from pg_semantic_operators.operators is deprecated. "
    "Use 'from pg_semantic_operators import ai_filter, ai_query, ai_image_filter, ai_image_describe' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["ai_filter", "ai_query", "ai_image_filter", "ai_image_describe"]
