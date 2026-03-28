"""
模型调用客户端
"""

import json
import re
from typing import Any, List
from .config import get_model_config


def _split_prompt(prompt: str) -> List[dict]:
    """
    尝试分离 system prompt 和 user prompt

    规则：
    - 如果 prompt 中包含 "```" 代码块或明显的分段，尝试分离
    - 否则整个作为 user message
    - 如果有 "现在请判断："、"请根据以上" 等标记，在标记处分割
    """
    # 尝试找到分割点
    split_patterns = [
        r'(?:现在请判断|请根据以上|请基于上述|根据上述规则)',
        r'\n\n(?:用户请求|User request|问题|Question)：',
    ]

    for pattern in split_patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            split_pos = match.end()
            system_part = prompt[:split_pos].strip()
            user_part = prompt[split_pos:].strip()

            if user_part:
                return [
                    {"role": "system", "content": system_part},
                    {"role": "user", "content": user_part}
                ]

    # 没有找到分割点，整个作为 user message
    return [{"role": "user", "content": prompt}]


def _call_openai(model_name: str, prompt: str, **kwargs) -> str:
    """调用 OpenAI API"""
    from openai import OpenAI

    config = get_model_config(model_name)
    client = OpenAI(
        api_key=config["api_key"],
        base_url=config.get("base_url", "https://api.openai.com/v1")
    )

    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "user", "content": prompt}],
        **kwargs
    )
    return response.choices[0].message.content


def _call_anthropic(model_name: str, prompt: str, **kwargs) -> str:
    """调用 Anthropic API"""
    import anthropic

    config = get_model_config(model_name)
    client = anthropic.Anthropic(api_key=config["api_key"])

    response = client.messages.create(
        model=config["model"],
        max_tokens=kwargs.get("max_tokens", 4096),
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def _call_ollama(model_name: str, prompt: str, **kwargs) -> str:
    """调用 Ollama 本地模型"""
    import requests
    
    config = get_model_config(model_name)
    base_url = config.get("base_url", "http://localhost:11434")
    
    response = requests.post(
        f"{base_url}/api/generate",
        json={
            "model": config["model"],
            "prompt": prompt,
            "stream": False
        },
        timeout=kwargs.get("timeout", 120)
    )
    response.raise_for_status()
    return response.json()["response"]


def _call_minimax(model_name: str, prompt: str, **kwargs) -> str:
    """调用 Minimax API (Anthropic 兼容)"""
    import requests

    config = get_model_config(model_name)
    base_url = config.get("base_url", "https://api.minimaxi.com/anthropic")
    api_key = config["api_key"]

    response = requests.post(
        f"{base_url}/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": config["model"],
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=kwargs.get("timeout", 120)
    )
    response.raise_for_status()
    response_json = response.json()

    # minimax API 返回的 content 数组可能包含多个元素
    # 需要找到 type 为 "text" 的元素
    for item in response_json.get("content", []):
        if item.get("type") == "text":
            return item.get("text", "")

    # 如果没找到 text 类型，返回第一个元素的 text（兼容旧格式）
    return response_json["content"][0].get("text", "")


def _call_glm(model_name: str, prompt: str, **kwargs) -> str:
    """调用智谱 GLM API (OpenAI 兼容)"""
    from openai import OpenAI

    config = get_model_config(model_name)
    client = OpenAI(
        api_key=config["api_key"],
        base_url=config.get("base_url", "https://open.bigmodel.cn/api/paas/v4")
    )

    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "user", "content": prompt}],
        **kwargs
    )
    return response.choices[0].message.content


PROVIDER_HANDLERS = {
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "ollama": _call_ollama,
    "minimax": _call_minimax,
    "glm": _call_glm,
}


def call_model(model_name: str, prompt: str, **kwargs) -> str:
    """
    调用模型
    
    Args:
        model_name: 模型名称 (如 "gpt-4o")
        prompt: 提示词
        **kwargs: 额外参数 (temperature, max_tokens 等)
    
    Returns:
        模型响应文本
    """
    config = get_model_config(model_name)
    provider = config["provider"]
    
    handler = PROVIDER_HANDLERS.get(provider)
    if not handler:
        raise ValueError(f"Unknown provider: {provider}")
    
    return handler(model_name, prompt, **kwargs)
