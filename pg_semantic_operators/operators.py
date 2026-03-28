# Backward compatibility shim - imports from new modular structure
# This file is deprecated. Use: from pg_semantic_operators import ai_filter, ai_query

import warnings

from .operators.ai_filter import ai_filter
from .operators.ai_query import ai_query

warnings.warn(
    "Direct import from pg_semantic_operators.operators is deprecated. "
    "Use 'from pg_semantic_operators import ai_filter, ai_query' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["ai_filter", "ai_query"]
