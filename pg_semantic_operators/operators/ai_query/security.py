"""Security module for ai_query operator.

Provides SQL injection prevention, dangerous operation filtering,
and query safety checks.
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_DANGEROUS_PATTERNS = [
    (re.compile(r";\s*DROP\s+", re.IGNORECASE), "检测到 DROP 语句，不允许删除数据库对象"),
    (re.compile(r";\s*DELETE\s+", re.IGNORECASE), "检测到 DELETE 语句，不允许删除数据"),
    (re.compile(r";\s*UPDATE\s+", re.IGNORECASE), "检测到 UPDATE 语句，不允许修改数据"),
    (re.compile(r";\s*INSERT\s+", re.IGNORECASE), "检测到 INSERT 语句，不允许插入数据"),
    (re.compile(r";\s*TRUNCATE\s+", re.IGNORECASE), "检测到 TRUNCATE 语句，不允许清空表"),
    (re.compile(r";\s*ALTER\s+", re.IGNORECASE), "检测到 ALTER 语句，不允许修改数据库结构"),
    (re.compile(r";\s*CREATE\s+", re.IGNORECASE), "检测到 CREATE 语句，不允许创建数据库对象"),
    (re.compile(r";\s*GRANT\s+", re.IGNORECASE), "检测到 GRANT 语句，不允许修改权限"),
    (re.compile(r";\s*REVOKE\s+", re.IGNORECASE), "检测到 REVOKE 语句，不允许修改权限"),
    (re.compile(r";\s*VACUUM\s+", re.IGNORECASE), "检测到 VACUUM 语句，不允许执行维护操作"),
    (re.compile(r"pg_catalog\.", re.IGNORECASE), "不允许直接访问系统目录"),
    (re.compile(r"information_schema\.", re.IGNORECASE), "不允许在生成的 SQL 中访问 information_schema"),
    (re.compile(r"pg_\w+\.", re.IGNORECASE), "不允许访问系统表"),
]

_INJECTION_PATTERNS = [
    (re.compile(r";\s*;\s*", re.IGNORECASE), "检测到可疑的多语句分隔符"),
    (re.compile(r"UNION\s+ALL\s+SELECT", re.IGNORECASE), "检测到 UNION 注入模式"),
    (re.compile(r"OR\s+1\s*=\s*1", re.IGNORECASE), "检测到恒真条件注入"),
    (re.compile(r"'\s*OR\s+'", re.IGNORECASE), "检测到字符串注入"),
    (re.compile(r";\s*COPY\s+", re.IGNORECASE), "检测到 COPY 语句，不允许数据导出"),
    (re.compile(r"INTO\s+OUTFILE", re.IGNORECASE), "检测到文件写入操作"),
    (re.compile(r"LOAD_FILE\s*\(", re.IGNORECASE), "检测到文件读取操作"),
    (re.compile(r"pg_read_file\s*\(", re.IGNORECASE), "检测到文件读取函数"),
    (re.compile(r"dblink\s*\(", re.IGNORECASE), "检测到数据库链接函数"),
    (re.compile(r"pg_execute_server_program\s*\(", re.IGNORECASE), "检测到系统命令执行函数"),
]

_MAX_JOIN_COUNT = 10
_MAX_NESTING_DEPTH = 5
_DEFAULT_MAX_LIMIT = 1000


def security_check(
    sql: str,
    read_only: bool = True,
    max_limit: int = _DEFAULT_MAX_LIMIT,
) -> Tuple[bool, Optional[str]]:
    """Check SQL for security issues.

    Args:
        sql: SQL string to check
        read_only: If True, only allow SELECT queries
        max_limit: Maximum LIMIT value allowed (0 = no limit check)

    Returns:
        Tuple of (is_safe, error_message)
    """
    if not sql or not sql.strip():
        return False, "SQL 为空"

    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()

    for pattern, message in _DANGEROUS_PATTERNS:
        if pattern.search(sql_stripped):
            return False, message

    for pattern, message in _INJECTION_PATTERNS:
        if pattern.search(sql_stripped):
            return False, message

    if read_only:
        first_keyword = sql_upper.split()[0] if sql_upper.split() else ""
        if first_keyword not in ("SELECT", "WITH", "EXPLAIN", "("):
            return False, f"只读模式下只允许 SELECT 查询，检测到: {first_keyword}"

        leading_statements = re.split(r";\s*", sql_stripped)
        for stmt in leading_statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            first_word = stmt.split()[0].upper() if stmt.split() else ""
            if first_word not in ("SELECT", "WITH", "EXPLAIN", ""):
                return False, f"只读模式下不允许 {first_word} 语句"

    join_count = len(re.findall(r"\bJOIN\b", sql_stripped, re.IGNORECASE))
    if join_count > _MAX_JOIN_COUNT:
        return False, f"JOIN 数量 ({join_count}) 超过限制 ({_MAX_JOIN_COUNT})"

    nesting = 0
    max_nesting = 0
    for ch in sql_stripped:
        if ch == "(":
            nesting += 1
            max_nesting = max(max_nesting, nesting)
        elif ch == ")":
            nesting -= 1
    if max_nesting > _MAX_NESTING_DEPTH:
        return False, f"子查询嵌套深度 ({max_nesting}) 超过限制 ({_MAX_NESTING_DEPTH})"

    return True, None


def ensure_limit(sql: str, default_limit: int = _DEFAULT_MAX_LIMIT) -> str:
    """Ensure SQL has a LIMIT clause, adding one if missing.

    Args:
        sql: SQL string
        default_limit: Default LIMIT to add if missing

    Returns:
        SQL with LIMIT clause
    """
    if default_limit <= 0:
        return sql

    sql_stripped = sql.strip()
    if not sql_stripped.endswith(";"):
        sql_stripped += ";"

    sql_upper = sql_stripped.upper()

    if re.search(r"\bLIMIT\s+\d+", sql_upper):
        return sql_stripped

    if "ORDER BY" in sql_upper:
        sql_stripped = re.sub(
            r"(ORDER\s+BY\s+[^\;]+)",
            rf"\1 LIMIT {default_limit}",
            sql_stripped,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        sql_stripped = sql_stripped.rstrip(";").strip() + f" LIMIT {default_limit};"

    return sql_stripped


def sanitize_sql(sql: str) -> str:
    """Basic SQL sanitization: remove trailing semicolons, normalize whitespace.

    Args:
        sql: Raw SQL string

    Returns:
        Sanitized SQL string
    """
    sql = sql.strip()

    sql = re.sub(r"\s+", " ", sql)

    if sql.endswith(";"):
        sql = sql[:-1].strip()

    return sql
