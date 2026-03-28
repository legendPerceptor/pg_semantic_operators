"""Semantic filtering operator"""

import json
from typing import Any
from ..client import call_model


# Exportable system prompt
AI_FILTER_SYSTEM_PROMPT = """你是数据判断助手。判断数据是否符合条件，只回答 true 或 false。

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


def ai_filter(model_name: str, condition: str, row_data: Any) -> bool:
    """
    Judge if row data matches semantic condition.

    Args:
        model_name: Model name (e.g., "gpt-4o")
        condition: Filter condition in natural language
        row_data: Row data (JSON string, dict, or object)

    Returns:
        True/False indicating if condition matches
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

    user_prompt = f"""条件: {condition}
数据: {json.dumps(row_json, ensure_ascii=False)}"""

    full_prompt = f"{AI_FILTER_SYSTEM_PROMPT}\n\n{user_prompt}"

    result = call_model(model_name, full_prompt).strip().lower()

    if "true" in result:
        return True
    elif "false" in result:
        return False
    else:
        return False
