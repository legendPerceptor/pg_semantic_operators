"""SQL validation and self-correction module for ai_query operator.

Provides SQL syntax validation, execution feedback, and iterative self-correction
to improve NL2SQL reliability.
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_ERROR_TAXONOMY = {
    "syntax_error": {
        "patterns": [
            r"syntax error",
            r"unexpected.*token",
            r"invalid.*syntax",
        ],
        "hint": "SQL 语法错误，请检查 SQL 语句的语法结构是否正确。",
    },
    "column_not_found": {
        "patterns": [
            r'column ".*" does not exist',
            r'column ".*" not found',
        ],
        "hint": "引用的列不存在，请检查列名是否正确，参考表结构中的列名。",
    },
    "table_not_found": {
        "patterns": [
            r'relation ".*" does not exist',
            r'table ".*" not found',
        ],
        "hint": "引用的表不存在，请检查表名是否正确，参考可用的表列表。",
    },
    "type_mismatch": {
        "patterns": [
            r"type mismatch",
            r"cannot cast",
            r"operator does not exist",
        ],
        "hint": "数据类型不匹配，请检查比较或运算中的数据类型是否一致。",
    },
    "join_missing": {
        "patterns": [
            r"invalid reference to FROM-clause entry",
            r"missing FROM-clause entry",
            r"ambiguous column reference",
        ],
        "hint": "JOIN 条件缺失或有歧义，请检查表之间的关联关系和外键约束。",
    },
    "function_not_found": {
        "patterns": [
            r'function .* does not exist',
        ],
        "hint": "调用的函数不存在，请检查函数名和参数类型是否正确。如果是语义算子，请参考算子注册表中的签名。",
    },
}


def classify_error(error_message: str) -> Tuple[str, str]:
    """Classify a SQL execution error and return error type and hint.

    Args:
        error_message: PostgreSQL error message

    Returns:
        Tuple of (error_type, correction_hint)
    """
    error_lower = error_message.lower()

    for error_type, info in _ERROR_TAXONOMY.items():
        for pattern in info["patterns"]:
            if re.search(pattern, error_lower):
                return error_type, info["hint"]

    return "unknown", f"SQL 执行出错: {error_message}"


def validate_sql_syntax(sql: str) -> Tuple[bool, Optional[str]]:
    """Basic client-side SQL validation without executing it.

    Checks for common issues:
    - Empty or whitespace-only SQL
    - Missing SELECT keyword
    - Dangerous statements (DROP, DELETE, etc.)
    - Unbalanced parentheses
    - Unbalanced quotes

    Args:
        sql: SQL string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not sql or not sql.strip():
        return False, "SQL 为空"

    sql_stripped = sql.strip()

    sql_upper = sql_stripped.upper()

    dangerous_keywords = ["DROP ", "DELETE ", "UPDATE ", "INSERT ", "TRUNCATE ", "ALTER ", "CREATE ", "GRANT ", "REVOKE "]
    for keyword in dangerous_keywords:
        if sql_upper.startswith(keyword) or f"; {keyword}" in sql_upper:
            if keyword.strip() not in ("SELECT",):
                return False, f"不允许的 SQL 操作: {keyword.strip()}"

    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH") and not sql_upper.startswith("("):
        if not sql_upper.startswith("EXPLAIN"):
            return False, "SQL 必须以 SELECT 或 WITH 开头"

    paren_count = 0
    for ch in sql_stripped:
        if ch == "(":
            paren_count += 1
        elif ch == ")":
            paren_count -= 1
        if paren_count < 0:
            return False, "括号不匹配：多余的右括号"
    if paren_count != 0:
        return False, f"括号不匹配：缺少 {paren_count} 个右括号"

    single_count = sql_stripped.count("'")
    if single_count % 2 != 0:
        return False, "单引号不匹配"

    return True, None


def build_correction_prompt(
    original_question: str,
    original_sql: str,
    error_message: str,
    schema_info: Optional[str] = None,
) -> str:
    """Build a prompt for LLM to correct a failed SQL query.

    Args:
        original_question: Original natural language question
        original_sql: The SQL that failed
        error_message: Error message from execution
        schema_info: Database schema for reference

    Returns:
        Correction prompt string
    """
    error_type, hint = classify_error(error_message)

    schema_section = ""
    if schema_info:
        schema_section = f"\n表结构参考:\n```sql\n{schema_info}\n```\n"

    return (
        f"以下 SQL 查询执行失败，请修正它。\n\n"
        f"原始问题: {original_question}\n\n"
        f"错误的 SQL:\n```sql\n{original_sql}\n```\n\n"
        f"错误类型: {error_type}\n"
        f"错误信息: {error_message}\n"
        f"修正提示: {hint}\n"
        f"{schema_section}\n"
        f"请输出修正后的 SQL，用 ```sql 代码块包裹。只输出修正后的 SQL，不要解释。"
    )


def self_correct(
    model_name: str,
    original_question: str,
    original_sql: str,
    error_message: str,
    schema_info: Optional[str] = None,
    call_model_fn=None,
    max_retries: int = 2,
) -> Tuple[str, bool]:
    """Attempt to self-correct a failed SQL query using LLM feedback.

    Args:
        model_name: LLM model name
        original_question: Original natural language question
        original_sql: The SQL that failed
        error_message: Error message from execution
        schema_info: Database schema for reference
        call_model_fn: Function to call the LLM model
        max_retries: Maximum number of correction attempts

    Returns:
        Tuple of (corrected_sql, was_corrected)
    """
    if call_model_fn is None:
        return original_sql, False

    current_sql = original_sql
    current_error = error_message

    for attempt in range(max_retries):
        correction_prompt = build_correction_prompt(
            original_question=original_question,
            original_sql=current_sql,
            error_message=current_error,
            schema_info=schema_info,
        )

        try:
            response = call_model_fn(model_name, correction_prompt)
            from .prompt_builder import extract_sql_from_response
            corrected_sql = extract_sql_from_response(response)

            if not corrected_sql or not corrected_sql.strip():
                continue

            is_valid, validation_error = validate_sql_syntax(corrected_sql)
            if not is_valid:
                current_error = validation_error
                current_sql = corrected_sql
                continue

            return corrected_sql, True

        except Exception as e:
            logger.warning(f"Self-correction attempt {attempt + 1} failed: {e}")
            continue

    return current_sql, False
