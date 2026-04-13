"""ai_query operator sub-package.

Provides the NL2SQL (Natural Language to SQL) operator with a six-stage pipeline:
1. Schema Linking - Enhanced schema info and relevant schema filtering
2. Prompt Engineering - Operator registry, few-shot examples, DDL representation
3. SQL Generation - Multi-candidate generation with CoT support
4. Validation & Self-Correction - Syntax validation and execution feedback
5. Candidate Selection - Self-consistency voting (future)
6. Security Check - SQL injection prevention and dangerous operation filtering
"""

from .core import ai_query, AI_QUERY_SYSTEM_PROMPT
from .schema_linking import get_schema_info_enhanced, get_relevant_schema, get_schema_info_basic
from .prompt_builder import build_prompt, extract_sql_from_response, OPERATOR_REGISTRY
from .validator import validate_sql_syntax, self_correct, classify_error
from .security import security_check, ensure_limit, sanitize_sql

__all__ = [
    "ai_query",
    "AI_QUERY_SYSTEM_PROMPT",
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
]
