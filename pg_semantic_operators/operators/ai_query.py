"""Natural language to SQL query operator"""

import re
from typing import Optional
from ..client import call_model


# Exportable system prompt base (without schema section)
AI_QUERY_SYSTEM_PROMPT_BASE = """你是一个 SQL 生成专家。根据用户的自然语言描述，生成对应的 SQL 查询语句。

{schema_section}

规则：
1. 优先返回 SQL 语句，用 ```sql 代码块包裹
2. 使用 PostgreSQL 语法
3. 如果无法确定表名或字段名，返回自然语言说明，告诉用户你需要什么信息
4. SQL 要简洁高效

输出格式示例：
```sql
SELECT * FROM orders WHERE status = 'completed' LIMIT 10;
```

或者如果信息不足：
抱歉，我需要更多信息来生成SQL。请告诉我您想查询的表名或字段名。"""


def ai_query(model_name: str, user_prompt: str, schema_info: Optional[str] = None) -> str:
    """
    Convert natural language to SQL query.

    Args:
        model_name: Model name (e.g., "gpt-4o")
        user_prompt: User's natural language query
        schema_info: Optional database schema information

    Returns:
        Generated SQL query or natural language response
    """
    schema_section = ""
    if schema_info:
        schema_section = f"""当前数据库的表结构信息：
{schema_info}

请基于上述表结构生成SQL查询。
"""

    system_prompt = AI_QUERY_SYSTEM_PROMPT_BASE.format(schema_section=schema_section)
    full_prompt = f"{system_prompt}\n\n用户请求: {user_prompt}"

    result = call_model(model_name, full_prompt)

    result = result.strip()

    if "```sql" in result:
        match = re.search(r'```sql\s*(.*?)\s*```', result, re.DOTALL)
        if match:
            return match.group(1).strip()

    if result.startswith("```sql"):
        result = result[6:]
    if result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]

    return result.strip()
