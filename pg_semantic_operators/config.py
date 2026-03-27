"""
模型配置管理
"""

import os
import json

def _load_env_file():
    """加载 .env 文件"""
    env_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.expanduser("~/.pg_semantic/.env"),
        "/etc/pg_semantic/.env",
    ]
    
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and key not in os.environ:
                            os.environ[key] = value

_load_env_file()

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
    },
    "minimax": {
        "provider": "minimax",
        "model": "MiniMax-M2.7",
        "api_key": os.getenv("MINIMAX_API_KEY"),
        "base_url": os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic")
    },
    "glm-4": {
        "provider": "glm",
        "model": "glm-4-flash",
        "api_key": os.getenv("GLM_API_KEY"),
        "base_url": os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    },
}

CONFIG_FILE = os.getenv("PG_SEMANTIC_CONFIG", "/etc/pg_semantic/models.json")


def get_model_config(model_name: str) -> dict:
    """获取模型配置"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            user_config = json.load(f)
            if model_name in user_config:
                return user_config[model_name]
    except Exception:
        pass
    
    if model_name in DEFAULT_CONFIG:
        return DEFAULT_CONFIG[model_name]
    
    raise ValueError(f"Unknown model: {model_name}")


def list_models() -> list[str]:
    """列出所有可用模型"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            user_config = json.load(f)
            return list(user_config.keys())
    except Exception:
        return list(DEFAULT_CONFIG.keys())
