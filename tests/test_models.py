"""
测试模型调用
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pg_semantic_operators.config import get_model_config, list_models, _load_env_file
from pg_semantic_operators.client import call_model, PROVIDER_HANDLERS


def test_list_models():
    """测试列出模型"""
    print("=" * 50)
    print("测试: 列出可用模型")
    print("=" * 50)
    models = list_models()
    print(f"可用模型: {models}")
    return models


def test_model_config(model_name: str):
    """测试获取模型配置"""
    print(f"\n{'=' * 50}")
    print(f"测试: 获取模型配置 - {model_name}")
    print("=" * 50)
    try:
        config = get_model_config(model_name)
        provider = config.get("provider")
        model = config.get("model")
        has_key = bool(config.get("api_key"))
        print(f"  Provider: {provider}")
        print(f"  Model: {model}")
        print(f"  API Key 已配置: {has_key}")
        if config.get("base_url"):
            print(f"  Base URL: {config.get('base_url')}")
        return True
    except ValueError as e:
        print(f"  错误: {e}")
        return False


def test_model_call(model_name: str, prompt: str = "Hello, respond with 'OK' only."):
    """测试调用模型"""
    print(f"\n{'=' * 50}")
    print(f"测试: 调用模型 - {model_name}")
    print("=" * 50)
    print(f"  Prompt: {prompt}")
    try:
        result = call_model(model_name, prompt)
        print(f"  响应: {result[:200]}..." if len(result) > 200 else f"  响应: {result}")
        return True
    except Exception as e:
        print(f"  错误: {type(e).__name__}: {e}")
        return False


def test_ai_filter(model_name: str):
    """测试 ai_filter 功能"""
    print(f"\n{'=' * 50}")
    print(f"测试: ai_filter - {model_name}")
    print("=" * 50)
    from pg_semantic_operators.operators import ai_filter
    
    test_cases = [
        ("金额大于1000", {"金额": 1500, "状态": "已完成"}),
        ("金额大于1000", {"金额": 500, "状态": "进行中"}),
        ("状态是已完成", {"状态": "已完成"}),
    ]
    
    for condition, data in test_cases:
        try:
            result = ai_filter(model_name, condition, data)
            print(f"  条件: {condition}, 数据: {data} => {result}")
        except Exception as e:
            print(f"  条件: {condition}, 数据: {data} => 错误: {e}")


def test_ai_query(model_name: str):
    """测试 ai_query 功能"""
    print(f"\n{'=' * 50}")
    print(f"测试: ai_query - {model_name}")
    print("=" * 50)
    from pg_semantic_operators.operators import ai_query
    
    try:
        result = ai_query(model_name, "找出金额大于1000的订单")
        print(f"  生成的SQL: {result}")
    except Exception as e:
        print(f"  错误: {e}")


def main():
    print("\n" + "=" * 60)
    print("PostgreSQL 语义算子 - 模型测试")
    print("=" * 60)
    
    _load_env_file()
    
    models = test_list_models()
    
    print("\n" + "-" * 60)
    print("配置检查")
    print("-" * 60)
    for model in models:
        test_model_config(model)
    
    print("\n" + "-" * 60)
    print("模型调用测试 (简单响应)")
    print("-" * 60)
    for model in models:
        config = get_model_config(model)
        if config.get("api_key") or config.get("provider") == "ollama":
            test_model_call(model)
        else:
            print(f"\n跳过 {model}: 未配置 API Key")
    
    print("\n" + "-" * 60)
    print("选择一个模型进行完整测试")
    print("-" * 60)
    
    available_models = []
    for model in models:
        config = get_model_config(model)
        if config.get("api_key") or config.get("provider") == "ollama":
            available_models.append(model)
    
    if available_models:
        test_model = available_models[0]
        print(f"使用 {test_model} 进行完整测试...")
        test_ai_filter(test_model)
        test_ai_query(test_model)
    else:
        print("没有可用的模型进行完整测试")


if __name__ == "__main__":
    main()
