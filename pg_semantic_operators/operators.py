"""
PostgreSQL 语义算子实现
"""

import json
import re
from .client import call_model


def ai_query(model_name: str, user_prompt: str, schema_info: str = None) -> str:
    """
    ai_query: 将自然语言转换为 SQL 查询
    
    Args:
        model_name: 模型名称 (如 "gpt-4o")
        user_prompt: 用户自然语言查询
        schema_info: 数据库schema信息（可选）
    
    Returns:
        生成的 SQL 语句或自然语言回答
    """
    schema_section = ""
    if schema_info:
        schema_section = f"""
当前数据库的表结构信息：
{schema_info}

请基于上述表结构生成SQL查询。
"""
    
    system_prompt = f"""你是一个 SQL 生成专家。根据用户的自然语言描述，生成对应的 SQL 查询语句。
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


def ai_filter(model_name: str, condition: str, row_data) -> bool:
    """
    ai_filter: 语义过滤判断
    
    Args:
        model_name: 模型名称 (如 "gpt-4o")
        condition: 过滤条件（自然语言描述）
        row_data: 行数据（JSON字符串、dict或JSONB）
    
    Returns:
        True/False 是否匹配
    """
    if row_data is None:
        return False
    
    try:
        if isinstance(row_data, str):
            row_json = json.loads(row_data)
        elif hasattr(row_data, 'to_dict'):
            row_json = row_data.to_dict()
        else:
            row_json = row_data
    except (json.JSONDecodeError, TypeError):
        row_json = {"raw": str(row_data)}
    
    system_prompt = """你是数据判断助手。判断数据是否符合条件，只回答 true 或 false。

【规则】
1. 严格按语义判断，只输出 true 或 false，不要其他内容
2. 数值大于1000是指 > 1000（不含1000）
3. 数值小于1000是指 < 1000（不含1000）
4. 数值大于等于1000是指 >= 1000

【示例】
输入：
条件：金额大于1000
数据：{"金额": 1500}
输出：true

输入：
条件：金额大于1000
数据：{"金额": 500}
输出：false

输入：
条件：金额大于1000
数据：{"金额": 1000}
输出：false

输入：
条件：状态是已完成
数据：{"状态": "已完成"}
输出：true

输入：
条件：状态是已完成
数据：{"状态": "进行中"}
输出：false

【待判断】"""
    
    user_prompt = f"""条件: {condition}
数据: {json.dumps(row_json, ensure_ascii=False)}"""
    
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    result = call_model(model_name, full_prompt).strip().lower()
    
    if "true" in result:
        return True
    elif "false" in result:
        return False
    else:
        return False
