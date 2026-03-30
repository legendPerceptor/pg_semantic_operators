"""AI Image operators for semantic filtering and description"""

from ..client import call_model_with_image
from .ai_image_helpers import load_image


AI_IMAGE_FILTER_SYSTEM_PROMPT = """你是图片判断助手。判断图片是否符合描述，只回答 true 或 false。

【规则】
1. 严格按语义判断，只输出 true 或 false，不要其他内容
2. 如果描述是图片类型（如"PNG图片"），检查图片格式
3. 如果描述是内容（如"包含猫"），检查图片内容

【示例】
输入：
描述：PNG 图片
图片：<image>
输出：true

输入：
描述：包含动物
图片：<image>
输出：false

【待判断】"""


def ai_image_filter(model_name: str, image_source: str, description: str) -> bool:
    """
    Judge if an image matches a semantic description.

    Args:
        model_name: Model name (e.g., "gpt-4o", "minimax")
        image_source: Image URL or local file path
        description: Natural language description to judge against

    Returns:
        True if image matches description, False otherwise

    Raises:
        ValueError: If image can't be loaded or model doesn't support vision
    """
    try:
        image_data = load_image(image_source)
    except Exception as e:
        raise ValueError(f"图片加载失败: {e}") from e

    user_prompt = f"描述: {description}"
    full_prompt = f"{AI_IMAGE_FILTER_SYSTEM_PROMPT}\n\n{user_prompt}"

    try:
        result = call_model_with_image(model_name, full_prompt, image_data).strip().lower()
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"图片判断失败: {e}") from e

    if "true" in result:
        return True
    elif "false" in result:
        return False
    else:
        return False


def ai_image_describe(model_name: str, image_source: str) -> str:
    """
    Generate a natural language description of an image.

    Args:
        model_name: Model name (e.g., "gpt-4o", "minimax")
        image_source: Image URL or local file path

    Returns:
        Text description of the image

    Raises:
        ValueError: If image can't be loaded or model doesn't support vision
    """
    try:
        image_data = load_image(image_source)
    except Exception as e:
        raise ValueError(f"图片加载失败: {e}") from e

    prompt = "请详细描述这张图片的内容，包括物体、场景、颜色等细节。"

    try:
        return call_model_with_image(model_name, prompt, image_data)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"图片描述失败: {e}") from e