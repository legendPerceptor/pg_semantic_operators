"""
快速测试单个模型
用法: python tests/quick_test.py <model_name>
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pg_semantic_operators import call_model, ai_filter, ai_query, list_models


def quick_test(model_name: str):
    print(f"\n{'=' * 60}")
    print(f"快速测试模型: {model_name}")
    print("=" * 60)
    
    print(f"\n可用模型: {list_models()}")
    
    print(f"\n--- 测试 1: 简单调用 ---")
    try:
        result = call_model(model_name, "Say 'Hello World' and nothing else.")
        print(f"响应: {result}")
    except Exception as e:
        print(f"错误: {e}")
        return
    
    print(f"\n--- 测试 2: ai_filter ---")
    try:
        result = ai_filter(model_name, "金额大于1000", {"金额": 1500})
        print(f"ai_filter('金额大于1000', {{'金额': 1500}}) = {result}")
    except Exception as e:
        print(f"错误: {e}")
    
    print(f"\n--- 测试 3: ai_query ---")
    try:
        result = ai_query(model_name, "找出最近一周的订单")
        print(f"生成的SQL: {result}")
    except Exception as e:
        print(f"错误: {e}")
    
    print(f"\n{'=' * 60}")
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python tests/quick_test.py <model_name>")
        print(f"可用模型: {list_models()}")
        sys.exit(1)
    
    model_name = sys.argv[1]
    quick_test(model_name)
