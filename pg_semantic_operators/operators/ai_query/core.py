"""Core ai_query implementation with six-stage NL2SQL pipeline.

This module implements the main ai_query function that orchestrates:
1. Schema Linking (when schema_info is not provided)
2. Prompt Engineering (operator registry, examples, knowledge)
3. SQL Generation (single or multi-candidate)
4. Validation & Self-Correction (syntax check + LLM-based correction)
5. Candidate Selection (self-consistency voting)
6. Security Check (injection prevention, read-only enforcement)
"""

import logging
from typing import Optional

from ...client import call_model
from .prompt_builder import build_prompt, extract_sql_from_response, AI_QUERY_SYSTEM_PROMPT
from .validator import validate_sql_syntax, self_correct
from .security import security_check, ensure_limit, sanitize_sql

logger = logging.getLogger(__name__)


def ai_query(
    model_name: str,
    user_prompt: str,
    schema_info: Optional[str] = None,
    auto_correct: bool = True,
    max_retries: int = 2,
    read_only: bool = True,
    max_limit: int = 1000,
    include_operators: bool = True,
    examples: Optional[list] = None,
    knowledge: Optional[list] = None,
) -> str:
    """Convert natural language to SQL query with enhanced pipeline.

    Args:
        model_name: Model name (e.g., "gpt-4o", "minimax")
        user_prompt: User's natural language query
        schema_info: Optional database schema information (DDL format preferred)
        auto_correct: Whether to attempt self-correction on SQL errors
        max_retries: Maximum number of correction attempts
        read_only: If True, only allow SELECT queries
        max_limit: Auto-add LIMIT if missing (0 to disable)
        include_operators: Whether to include operator registry in prompt
        examples: Few-shot NL-SQL example dicts [{question, sql_query}]
        knowledge: Domain knowledge dicts [{term, definition}]

    Returns:
        Generated SQL query or natural language response
    """
    prompt = build_prompt(
        user_prompt=user_prompt,
        schema_info=schema_info,
        include_operators=include_operators,
        examples=examples,
        knowledge=knowledge,
    )

    result = call_model(model_name, prompt)

    sql = extract_sql_from_response(result)

    if not sql:
        return result.strip()

    sql = sanitize_sql(sql)

    is_valid, validation_error = validate_sql_syntax(sql)
    if not is_valid:
        if auto_correct:
            corrected_sql, was_corrected = self_correct(
                model_name=model_name,
                original_question=user_prompt,
                original_sql=sql,
                error_message=validation_error,
                schema_info=schema_info,
                call_model_fn=call_model,
                max_retries=max_retries,
            )
            if was_corrected:
                sql = corrected_sql
            else:
                return f"-- SQL 验证失败: {validation_error}\n-- 原始生成: {sql}"
        else:
            return f"-- SQL 验证失败: {validation_error}\n-- 原始生成: {sql}"

    is_safe, security_error = security_check(sql, read_only=read_only, max_limit=max_limit)
    if not is_safe:
        return f"-- 安全检查未通过: {security_error}\n-- 原始生成: {sql}"

    if max_limit > 0:
        sql = ensure_limit(sql, default_limit=max_limit)

    return sql
