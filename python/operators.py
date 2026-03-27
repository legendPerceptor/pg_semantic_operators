"""
PostgreSQL 语义算子实现
"""

import json
from .client import call_model


# ========== ai_query ==========

def ai_query(model_name: str, user_prompt: str) -> str:
    """
    ai_query: 将自然语言转换为 SQL 查询
    
    Args:
        model_name: 模型名称 (如 "gpt-4o")
        user_prompt: 用户自然语言查询
    
    Returns:
        生成的 SQL 语句
    """
    # 构建系统提示词
    system_prompt = """你是一个 SQL 生成专家。根据用户的自然语言描述，生成对应的 SQL 查询语句。

规则：
1. 只返回 SQL 语句，不要其他解释
2. 使用通用的 PostgreSQL 语法
3. 根据上下文合理猜测表名和字段名
4. 如果信息不足，在注释中说明

输出格式：
```sql
SELECT ...
```

示例：
输入: "找出最近一周的订单"
输出: 
```sql
SELECT * FROM orders 
WHERE created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
```"""
    
    full_prompt = f"{system_prompt}\n\n用户请求: {user_prompt}"
    
    result = call_model(model_name, full_prompt)
    
    # 提取 SQL (处理 markdown 代码块)
    result = result.strip()
    if result.startswith("```sql"):
        result = result[6:]
    if result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]
    
    return result.strip()


# ========== ai_filter ==========

def ai_filter(model_name: str, row_json: str) -> bool:
    """
    ai_filter: 语义过滤判断
    
    Args:
        model_name: 模型名称 (如 "gpt-4o")
        row_json: 行的 JSON 表示
    
    Returns:
        True/False 是否匹配
    """
    # 解析 JSON
    try:
        if isinstance(row_json, str):
            row_data = json.loads(row_json)
        else:
            row_data = row_json
    except json.JSONDecodeError:
        return False
    
    # 构建系统提示词
    system_prompt = """你是一个智能过滤器。根据用户提供的过滤条件，判断每一行数据是否符合条件。

规则：
1. 只返回 "true" 或 "false"
2. 严格根据语义判断，不要过度推理
3. 字段名为中文时，按字面意思理解

示例：
输入: {"条件": "金额大于1000", "数据": {"金额": 500}}
输出: false

输入: {"条件": "状态是已完成", "数据": {"状态": "已完成", "金额": 2000}}
输出: true"""
    
    # 构建提示词
    user_prompt = f"数据: {json.dumps(row_data, ensure_ascii=False)}"
    
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    result = call_model(model_name, full_prompt).strip().lower()
    
    # 解析结果
    if "true" in result:
        return True
    elif "false" in result:
        return False
    else:
        # 默认返回 False，避免误判
        return False