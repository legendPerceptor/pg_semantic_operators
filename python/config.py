# 模型配置
# 格式: 模型名 -> {"provider": "openai|anthropic|ollama", "model": "模型ID", "api_key": "..."}

import os

# 默认从环境变量读取
DEFAULT_CONFIG = {
    "gpt-4o": {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    },
    "claude-3-5-sonnet": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": os.getenv("ANTHROPIC_API_KEY")
    },
    "qwen-coder": {
        "provider": "ollama",
        "model": "qwen2.5-coder:7b",
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    }
}

# 用户自定义配置路径
CONFIG_FILE = os.getenv("PG_SEMANTIC_CONFIG", "/etc/pg_semantic/models.json")


def get_model_config(model_name: str) -> dict:
    """获取模型配置"""
    # 先尝试从文件加载
    try:
        import json
        with open(CONFIG_FILE, 'r') as f:
            user_config = json.load(f)
            if model_name in user_config:
                return user_config[model_name]
    except Exception:
        pass
    
    # 回退到默认配置
    if model_name in DEFAULT_CONFIG:
        return DEFAULT_CONFIG[model_name]
    
    raise ValueError(f"Unknown model: {model_name}")


def list_models() -> list[str]:
    """列出所有可用模型"""
    try:
        import json
        with open(CONFIG_FILE, 'r') as f:
            user_config = json.load(f)
            return list(user_config.keys())
    except Exception:
        return list(DEFAULT_CONFIG.keys())