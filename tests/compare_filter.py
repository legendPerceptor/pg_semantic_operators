"""
对比不同模型的 ai_filter 效果
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pg_semantic_operators.config import _load_env_file, list_models, get_model_config
from pg_semantic_operators.client import call_model
from pg_semantic_operators import AI_FILTER_SYSTEM_PROMPT

_load_env_file()

# Use the actual prompt from the operator module
system_prompt = AI_FILTER_SYSTEM_PROMPT

test_cases = [
    ("金额大于1000", {"金额": 1500}, True),
    ("金额大于1000", {"金额": 500}, False),
    ("状态是已完成", {"状态": "已完成"}, True),
]

print("=" * 80)
print("对比不同模型的 ai_filter 效果")
print("=" * 80)

models = list_models()

for model_name in models:
    config = get_model_config(model_name)
    if not config.get("api_key") and config.get("provider") != "ollama":
        continue

    print(f"\n{'=' * 80}")
    print(f"模型: {model_name}")
    print(f"{'=' * 80}")

    for condition, row_data, expected in test_cases:
        user_prompt = f"""条件: {condition}
数据: {json.dumps(row_data, ensure_ascii=False)}"""

        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        try:
            result = call_model(model_name, full_prompt)
            result_lower = result.strip().lower()

            # 检查 true/false - 按照/operators.py中ai_filter的逻辑
            if "true" in result_lower:
                actual = True
            elif "false" in result_lower:
                actual = False
            else:
                # 模糊情况，打印原始响应
                actual = None

            status = "✓" if actual == expected else "✗"
            if actual is None:
                print(f"  {status} 条件: {condition}, 数据: {row_data}")
                print(f"     期望: {expected}, 实际: 模糊 (响应: {result[:100]})")
            else:
                print(f"  {status} 条件: {condition}, 数据: {row_data}")
                print(f"     期望: {expected}, 实际: {actual}")

        except Exception as e:
            print(f"  ✗ 条件: {condition}, 数据: {row_data}")
            print(f"     错误: {e}")

print(f"\n{'=' * 80}")
