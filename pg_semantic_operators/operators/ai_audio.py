"""AI Audio operators for semantic filtering and description"""

from ..client import call_model_with_audio
from .ai_audio_helpers import load_audio


AI_AUDIO_FILTER_SYSTEM_PROMPT = """你是音频判断助手。判断音频是否符合描述，只回答 true 或 false。

【规则】
1. 严格按语义判断，只输出 true 或 false，不要其他内容
2. 如果描述是语言类型（如"英文"），检查音频语言
3. 如果描述是内容（如"包含天气预报"），检查音频内容

【示例】
输入：
描述：英文
音频：<audio>
输出：true

输入：
描述：包含天气预报
音频：<audio>
输出：false

【待判断】"""


def ai_audio_filter(model_name: str, audio_source: str, description: str) -> bool:
    """
    Judge if an audio matches a semantic description.

    Args:
        model_name: Model name (e.g., "gpt-4o-audio-preview")
        audio_source: Audio URL or local file path
        description: Natural language description to judge against

    Returns:
        True if audio matches description, False otherwise

    Raises:
        ValueError: If audio can't be loaded or model doesn't support audio
    """
    try:
        audio_data = load_audio(audio_source)
    except Exception as e:
        raise ValueError(f"音频加载失败: {e}") from e

    user_prompt = f"描述: {description}"
    full_prompt = f"{AI_AUDIO_FILTER_SYSTEM_PROMPT}\n\n{user_prompt}"

    try:
        result = call_model_with_audio(model_name, full_prompt, audio_data).strip().lower()
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"音频判断失败: {e}") from e

    if "true" in result:
        return True
    elif "false" in result:
        return False
    else:
        return False


def ai_audio_describe(model_name: str, audio_source: str) -> str:
    """
    Transcribe and describe audio content.

    Args:
        model_name: Model name (e.g., "gpt-4o-audio-preview")
        audio_source: Audio URL or local file path

    Returns:
        Text description / transcription of the audio

    Raises:
        ValueError: If audio can't be loaded or model doesn't support audio
    """
    try:
        audio_data = load_audio(audio_source)
    except Exception as e:
        raise ValueError(f"音频加载失败: {e}") from e

    prompt = "请详细描述这段音频的内容，包括语言、说话人数量、主题等细节。"

    try:
        return call_model_with_audio(model_name, prompt, audio_data)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"音频描述失败: {e}") from e