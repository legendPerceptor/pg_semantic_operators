"""
详细调试 gpt-4o 的 ai_filter 响应
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pg_semantic_operators.config import _load_env_file
from pg_semantic_operators.client import call_model
from pg_semantic_operators import AI_FILTER_SYSTEM_PROMPT

_load_env_file()

model_name = "gpt-4o"
condition = "金额大于1000"
row_data = {"金额": 1500}

# Use the actual prompt from the operator module
system_prompt = AI_FILTER_SYSTEM_PROMPT

user_prompt = f"""条件：{condition}
数据：{json.dumps(row_data, ensure_ascii=False)}"""

full_prompt = f"{system_prompt}\n\n{user_prompt}"

print("=" * 80)
print(f"测试 {model_name}")
print("=" * 80)
print(f"\n完整 prompt:")
print("-" * 80)
print(full_prompt)
print("-" * 80)

result = call_model(model_name, full_prompt)

print(f"\n原始响应:")
print(f"  {repr(result)}")

print(f"\n响应长度: {len(result)} 字符")
print(f"响应内容 (前500字符):")
print(f"  {result[:500]}")

print(f"\n分析:")
result_lower = result.strip().lower()
print(f"  转小写并去空格: {repr(result_lower[:100])}")
print(f"  包含 'true': {'true' in result_lower}")
print(f"  包含 'false': {'false' in result_lower}")

# 检查是否同时包含
if 'true' in result_lower and 'false' in result_lower:
    print(f"  ⚠️ 同时包含 true 和 false！")
    # 找到最后出现的位置
    last_true = result_lower.rfind('true')
    last_false = result_lower.rfind('false')
    print(f"    最后的 'true' 位置: {last_true}")
    print(f"    最后的 'false' 位置: {last_false}")

    if last_false > last_true:
        print(f"    → 最终判断: False (false 更靠后)")
    else:
        print(f"    → 最终判断: True (true 更靠后)")
