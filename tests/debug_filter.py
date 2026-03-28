"""
调试 ai_filter 功能
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pg_semantic_operators.config import _load_env_file
from pg_semantic_operators.client import call_model

_load_env_file()

model_name = "minimax"
condition = "金额大于1000"
row_data = {"金额": 1500}

system_prompt = """你是一个智能过滤器。根据用户提供的过滤条件，判断每一行数据是否符合条件。

规则：
1. 只返回 "true" 或 "false"，不要其他任何内容
2. 严格根据语义判断
3. 如果条件模糊，倾向于返回 "false"
4. 数值比较要精确（如"大于100"表示 > 100）

示例：
条件: "金额大于1000"
数据: {"金额": 500, "状态": "已完成"}
输出: false

条件: "状态是已完成"
数据: {"状态": "已完成", "金额": 2000}
输出: true

条件: "名字包含张"
数据: {"名字": "张三", "年龄": 25}
输出: true"""

user_prompt = f"""条件: {condition}
数据: {json.dumps(row_data, ensure_ascii=False)}"""

full_prompt = f"{system_prompt}\n\n{user_prompt}"

print("=" * 60)
print("测试 ai_filter 功能")
print("=" * 60)
print(f"\n模型: {model_name}")
print(f"条件: {condition}")
print(f"数据: {row_data}")
print(f"\n发送的 prompt:")
print("-" * 60)
print(full_prompt[:500] + "..." if len(full_prompt) > 500 else full_prompt)
print("-" * 60)

result = call_model(model_name, full_prompt)

print(f"\n原始响应:")
print(f"  {repr(result)}")

print(f"\n处理后的结果:")
result_lower = result.strip().lower()
print(f"  转小写: {result_lower}")
print(f"  包含 'true': {'true' in result_lower}")
print(f"  包含 'false': {'false' in result_lower}")

if "true" in result_lower:
    final_result = True
elif "false" in result_lower:
    final_result = False
else:
    final_result = False

print(f"\n最终结果: {final_result}")
print(f"期望结果: True")
print(f"测试 {'✓ 通过' if final_result == True else '✗ 失败'}")
