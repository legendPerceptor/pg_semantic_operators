"""
模型配置管理
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

_user_config = None

# 从当前文件向上查找 pyproject.toml 所在目录作为项目根目录
_project_root = Path(__file__).resolve().parent.parent
while not (_project_root / "pyproject.toml").exists():
    if _project_root.parent == _project_root:
        break
    _project_root = _project_root.parent

load_dotenv(_project_root / ".env")

_ALL_MODELS = {
    "gpt-4o": {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    },
    "gpt-4o-audio-preview": {
        "provider": "openai",
        "model": "gpt-4o-audio-preview",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    },
    "claude-3-5-sonnet": {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "qwen-coder": {
        "provider": "ollama",
        "model": "qwen2.5-coder:7b",
        "api_key_env": "OLLAMA_API_KEY",
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    },
    "minimax": {
        "provider": "minimax",
        "model": "MiniMax-M2.7",
        "api_key_env": "MINIMAX_API_KEY",
        "base_url": os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic"),
    },
    "glm-4": {
        "provider": "glm",
        "model": "glm-4-flash",
        "api_key_env": "GLM_API_KEY",
        "base_url": os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
    },
}


def _build_default_config() -> dict:
    """根据已配置的 API key 筛选可用的模型配置。"""
    config = {}
    for name, info in _ALL_MODELS.items():
        env_var = info.get("api_key_env")
        if env_var:
            api_key = os.getenv(env_var)
            if not api_key:
                continue
            entry = {k: v for k, v in info.items() if k != "api_key_env"}
            entry["api_key"] = api_key
        else:
            entry = {k: v for k, v in info.items() if k != "api_key_env"}
        config[name] = entry
    return config


DEFAULT_CONFIG = _build_default_config()

print("default config: ", DEFAULT_CONFIG)

CONFIG_FILE = os.getenv("PG_SEMANTIC_CONFIG", str(_project_root / "models.json"))


def _find_config_file() -> str | None:
    """查找配置文件"""
    if os.path.exists(CONFIG_FILE):
        return CONFIG_FILE
    return None


def _load_user_config() -> dict:
    """加载用户配置文件"""
    global _user_config
    if _user_config is not None:
        return _user_config
    
    config_path = _find_config_file()
    if config_path:
        try:
            with open(config_path, 'r') as f:
                _user_config = json.load(f)
                return _user_config
        except Exception:
            pass
    
    return {}


def get_model_config(model_name: str) -> dict:
    """获取模型配置"""
    user_config = _load_user_config()
    
    if model_name in user_config:
        return user_config[model_name]
    
    if not user_config and model_name in DEFAULT_CONFIG:
        return DEFAULT_CONFIG[model_name]
    
    raise ValueError(f"Unknown model: {model_name}")


def list_models() -> list[str]:
    """列出所有可用模型"""
    user_config = _load_user_config()
    
    if user_config:
        return list(user_config.keys())
    
    return list(DEFAULT_CONFIG.keys())
