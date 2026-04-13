"""Prompt builder module for ai_query operator.

Constructs enhanced prompts with operator registry, few-shot examples,
domain knowledge, and DDL-style schema representation.
"""

import re
from typing import Dict, List, Optional


OPERATOR_REGISTRY = {
    "ai_filter": {
        "signature": "ai_filter(model_name TEXT, condition TEXT, row_data JSONB) -> BOOLEAN",
        "description": (
            "对每一行数据做语义过滤判断。condition 是自然语言过滤条件，"
            "row_data 是当前行的 JSONB 数据。返回 true 表示该行满足条件。"
            "适用于标准 SQL WHERE 无法表达的语义过滤场景。"
        ),
        "example": (
            "SELECT * FROM orders\n"
            "WHERE ai_filter('minimax', '这是一个高价值订单',\n"
            "  jsonb_build_object('customer', customer_name, 'amount', amount, 'status', status));"
        ),
    },
    "ai_query": {
        "signature": "ai_query(model_name TEXT, user_prompt TEXT, schema_info TEXT) -> TEXT",
        "description": (
            "将自然语言转换为 SQL 查询。可以嵌套使用 ai_query 来构建子查询。"
            "返回生成的 SQL 文本。"
        ),
        "example": (
            "SELECT ai_query('minimax', '找出金额大于1000的订单', get_schema_info());"
        ),
    },
    "ai_image_filter": {
        "signature": "ai_image_filter(model_name TEXT, image_source TEXT, description TEXT) -> BOOLEAN",
        "description": (
            "判断图片是否符合给定的描述。image_source 是图片 URL 或路径，"
            "description 是自然语言描述。返回 true 表示图片符合描述。"
        ),
        "example": (
            "SELECT * FROM products\n"
            "WHERE ai_image_filter('gpt-4o', image_url, '产品图片中包含红色元素');"
        ),
    },
}

AI_QUERY_SYSTEM_PROMPT = """你是一个 SQL 生成专家。根据用户的自然语言描述，生成对应的 PostgreSQL SQL 查询语句。

{schema_section}

{operator_section}

{knowledge_section}

{example_section}

规则：
1. 优先返回 SQL 语句，用 ```sql 代码块包裹
2. 使用 PostgreSQL 语法
3. 如果用户的问题涉及语义理解（如"高价值"、"重要的"、"相关的"等模糊概念），优先使用 ai_filter 等语义算子而非硬编码条件
4. 如果无法确定表名或字段名，返回自然语言说明，告诉用户你需要什么信息
5. SQL 要简洁高效
6. 只生成 SELECT 查询，不要生成 INSERT/UPDATE/DELETE/DROP 等修改数据的语句
7. 如果查询可能返回大量结果，请添加合理的 LIMIT 子句

输出格式示例：
```sql
SELECT * FROM orders WHERE status = 'completed' LIMIT 10;
```

或者如果信息不足：
抱歉，我需要更多信息来生成SQL。请告诉我您想查询的表名或字段名。"""


def _build_operator_section() -> str:
    """Build the operator registry section for the prompt."""
    lines = ["当前数据库中可用的自定义语义算子：", ""]
    for name, info in OPERATOR_REGISTRY.items():
        lines.append(f"### {name}")
        lines.append(f"签名: {info['signature']}")
        lines.append(f"说明: {info['description']}")
        lines.append(f"示例:")
        lines.append(f"```sql")
        lines.append(info["example"])
        lines.append(f"```")
        lines.append("")
    return "\n".join(lines)


def _build_knowledge_section(knowledge: Optional[List[Dict[str, str]]] = None) -> str:
    """Build the domain knowledge section for the prompt."""
    if not knowledge:
        return ""
    lines = ["业务领域知识：", ""]
    for item in knowledge:
        term = item.get("term", "")
        definition = item.get("definition", "")
        if term and definition:
            lines.append(f"- {term}: {definition}")
    lines.append("")
    return "\n".join(lines)


def _build_example_section(examples: Optional[List[Dict[str, str]]] = None) -> str:
    """Build the few-shot example section for the prompt."""
    if not examples:
        return ""
    lines = ["参考示例：", ""]
    for i, ex in enumerate(examples, 1):
        question = ex.get("question", "")
        sql = ex.get("sql_query", "")
        if question and sql:
            lines.append(f"示例 {i}:")
            lines.append(f"问题: {question}")
            lines.append(f"```sql")
            lines.append(sql)
            lines.append(f"```")
            lines.append("")
    return "\n".join(lines)


def build_prompt(
    user_prompt: str,
    schema_info: Optional[str] = None,
    include_operators: bool = True,
    examples: Optional[List[Dict[str, str]]] = None,
    knowledge: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Build the complete prompt for NL2SQL generation.

    Args:
        user_prompt: User's natural language query
        schema_info: Database schema information (DDL format preferred)
        include_operators: Whether to include operator registry in prompt
        examples: Few-shot NL-SQL examples
        knowledge: Domain knowledge entries

    Returns:
        Complete prompt string for LLM
    """
    schema_section = ""
    if schema_info:
        schema_section = (
            "当前数据库的表结构信息（DDL格式）：\n"
            "```sql\n"
            f"{schema_info}\n"
            "```\n\n"
            "请基于上述表结构生成 SQL 查询。注意外键关系用于确定 JOIN 条件。"
        )

    operator_section = ""
    if include_operators:
        operator_section = _build_operator_section()

    knowledge_section = _build_knowledge_section(knowledge)
    example_section = _build_example_section(examples)

    system_prompt = AI_QUERY_SYSTEM_PROMPT.format(
        schema_section=schema_section,
        operator_section=operator_section,
        knowledge_section=knowledge_section,
        example_section=example_section,
    )

    return f"{system_prompt}\n\n用户请求: {user_prompt}"


def extract_sql_from_response(response: str) -> str:
    """Extract SQL from LLM response, handling various output formats.

    Args:
        response: Raw LLM response text

    Returns:
        Extracted SQL string
    """
    result = response.strip()

    if "```sql" in result:
        match = re.search(r"```sql\s*(.*?)\s*```", result, re.DOTALL)
        if match:
            return match.group(1).strip()

    if result.startswith("```sql"):
        result = result[6:]
    if result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]

    return result.strip()
