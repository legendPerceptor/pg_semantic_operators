"""AI Audio operators for semantic filtering and description"""

from ..client import call_model_with_audio
from .ai_audio_helpers import load_audio


AI_AUDIO_FILTER_SYSTEM_PROMPT = """你是音频判断助手。判断音频是否符合描述，只回答 true 或 false。

【判断规则】
1. 只输出 true 或 false，不要其他任何内容
2. 语言判断（如"中文"、"英文"）：检查音频使用的语言
3. 内容判断（如"包含天气预报"、"提到产品"）：检查音频文字内容是否包含相关含义
4. 精确短语（如"我们都是最棒的"）：检查音频转录文字是否包含这个短语或非常相似的表述
5. 时长判断（如"不超过10秒"、"超过1分钟"）：根据音频实际时长判断，允许小幅误差

【判断原则】
- 对于具体短语，应该对比音频转录文字来判断
- 对于时长，先估计音频长度再判断
- 不要猜测或假设，用音频实际内容判断
- 当描述明显匹配音频内容时返回 true

【示例】
描述：中文 → 音频是中文 → true
描述：英文 → 音频是中文 → false
描述：包含天气预报 → 音频内容有天气预报 → true
描述：我们都是最棒的 → 音频文字包含这句话 → true
描述：时长不超过10秒 → 音频约10秒或更短 → true
描述：时长超过1分钟 → 音频约10秒 → false

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