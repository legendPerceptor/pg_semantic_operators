"""
调试 minimax API 调用
"""

import sys
import os
import json
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pg_semantic_operators.config import get_model_config, _load_env_file

_load_env_file()

model_name = "minimax"
config = get_model_config(model_name)

print("=" * 60)
print("调试 minimax API 调用")
print("=" * 60)
print(f"\n配置信息:")
print(f"  Provider: {config.get('provider')}")
print(f"  Model: {config.get('model')}")
print(f"  Base URL: {config.get('base_url')}")
print(f"  Has API Key: {bool(config.get('api_key'))}")

api_key = config["api_key"]
base_url = config.get("base_url", "https://api.minimaxi.com/anthropic")

print(f"\n发送请求到: {base_url}/v1/messages")

try:
    response = requests.post(
        f"{base_url}/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": config["model"],
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": "Say 'Hello World' and nothing else."}]
        },
        timeout=120
    )

    print(f"\n状态码: {response.status_code}")
    print(f"\n响应头:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")

    print(f"\n响应内容:")
    try:
        response_json = response.json()
        print(json.dumps(response_json, indent=2, ensure_ascii=False))

        # 尝试解析
        if "content" in response_json:
            print(f"\n✓ 响应包含 'content' 字段")
            if isinstance(response_json["content"], list) and len(response_json["content"]) > 0:
                print(f"  content 类型: {type(response_json['content'][0])}")
                print(f"  content[0] 的键: {response_json['content'][0].keys() if isinstance(response_json['content'][0], dict) else 'N/A'}")

                if "text" in response_json["content"][0]:
                    print(f"\n✓ 找到文本内容:")
                    print(f"  {response_json['content'][0]['text']}")
                else:
                    print(f"\n✗ content[0] 中没有 'text' 字段")

        # 检查错误
        if "error" in response_json:
            print(f"\n✗ API 返回错误:")
            print(f"  {response_json['error']}")

    except json.JSONDecodeError as e:
        print(f"无法解析 JSON: {e}")
        print(f"原始响应:\n{response.text}")

except Exception as e:
    print(f"\n✗ 请求失败:")
    print(f"  错误类型: {type(e).__name__}")
    print(f"  错误信息: {e}")
    import traceback
    traceback.print_exc()
