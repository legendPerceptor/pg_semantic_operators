"""模型调用客户端"""

import json
from typing import Any
from .config import get_model_config


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


PROVIDER_HANDLERS = {
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "ollama": _call_ollama
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