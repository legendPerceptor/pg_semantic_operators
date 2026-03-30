# AI Image Operators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `ai_image_filter` and `ai_image_describe` functions supporting GPT-4o and Minimax models with URL and local file image sources.

**Architecture:** New `ai_image.py` module with image loading helpers, modify `client.py` to add image-capable provider handlers, expose via SQL.

**Tech Stack:** Python 3, plpython3u, requests (for URL fetching), OpenAI/Minimax APIs

---

## File Structure

| File | Action | Purpose |
|------|--------|---------|
| `pg_semantic_operators/operators/ai_image.py` | Create | Image operators (filter & describe) |
| `pg_semantic_operators/operators/__init__.py` | Modify | Export new functions |
| `pg_semantic_operators/client.py` | Modify | Add `_call_openai_with_image` and `_call_minimax_with_image` |
| `pg_semantic_operators/operators.py` | Modify | Re-export new functions |
| `sql/pg_semantic_operators--1.0.sql` | Modify | Add SQL function definitions |
| `tests/test_image.py` | Create | Test image operators |

---

## Task 1: Image Loading Helper

**Files:**
- Create: `pg_semantic_operators/operators/ai_image_helpers.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_image_helpers.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pg_semantic_operators.operators.ai_image_helpers import load_image

def test_load_image_from_url():
    """Test loading image from URL"""
    url = "https://httpbin.org/image/png"
    result = load_image(url)
    assert result is not None
    assert "data" in result
    assert result["media_type"] == "image/png"

def test_load_image_from_local_file():
    """Test loading image from local file"""
    import tempfile
    import base64

    # Create a small test PNG (1x1 red pixel)
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    )
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(png_data)
        temp_path = f.name

    try:
        result = load_image(temp_path)
        assert result is not None
        assert result["media_type"] == "image/png"
    finally:
        os.unlink(temp_path)

def test_load_image_invalid_source():
    """Test error on invalid source"""
    import pytest
    with pytest.raises(ValueError, match="本地图片文件不存在"):
        load_image("/nonexistent/path/to/image.png")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_image_helpers.py -v
```
Expected: FAIL - module not found

- [ ] **Step 3: Write minimal implementation**

```python
# pg_semantic_operators/operators/ai_image_helpers.py
"""Image loading utilities for AI image operators"""

import base64
import re
import os
from typing import Dict
import requests


def load_image(source: str) -> Dict[str, str]:
    """
    Load an image from URL or local file.

    Args:
        source: URL (http:// or https://) or local file path

    Returns:
        Dict with 'data' (base64 encoded image) and 'media_type'

    Raises:
        ValueError: If image cannot be loaded
    """
    if source.startswith(("http://", "https://")):
        return _load_from_url(source)
    else:
        return _load_from_file(source)


def _load_from_url(url: str) -> Dict[str, str]:
    """Load image from URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"无法加载图片 URL: {url}") from e

    content = response.content

    # Detect media type from content or URL
    media_type = _detect_media_type(content, url)

    encoded = base64.b64encode(content).decode("utf-8")
    return {"data": encoded, "media_type": media_type}


def _load_from_file(path: str) -> Dict[str, str]:
    """Load image from local file"""
    if not os.path.exists(path):
        raise ValueError(f"本地图片文件不存在: {path}")

    with open(path, "rb") as f:
        content = f.read()

    media_type = _detect_media_type(content, path)
    encoded = base64.b64encode(content).decode("utf-8")
    return {"data": encoded, "media_type": media_type}


def _detect_media_type(content: bytes, source: str) -> str:
    """Detect media type from content or file extension"""
    # Check magic bytes for common image formats
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if content[:2] == b"\xff\xd8":
        return "image/jpeg"
    if content[:4] == b"GIF87a" or content[:4] == b"GIF89a":
        return "image/gif"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content[:4] == b"II\x2a\x00" or content[:4] == b"MM\x00\x2a":
        return "image/tiff"

    # Fall back to extension
    ext = os.path.splitext(source)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }
    return mime_map.get(ext, "application/octet-stream")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_image_helpers.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pg_semantic_operators/operators/ai_image_helpers.py tests/test_image_helpers.py
git commit -m "feat: add image loading helper for URL and local files

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: OpenAI Image Support

**Files:**
- Modify: `pg_semantic_operators/client.py:149-177`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_image_client.py (add to existing file)
def test_call_openai_with_image():
    """Test OpenAI API with image content"""
    from pg_semantic_operators.client import call_model_with_image

    # Simple test with a 1x1 transparent GIF
    image_data = {
        "data": "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
        "media_type": "image/gif"
    }
    result = call_model_with_image("gpt-4o", "描述这个图片", image_data)
    assert result is not None
    assert len(result) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_image_client.py::test_call_openai_with_image -v
```
Expected: FAIL - function not defined

- [ ] **Step 3: Write implementation**

Add to `client.py`:

```python
def _call_openai_with_image(model_name: str, prompt: str, image_data: Dict[str, str], **kwargs) -> str:
    """
    Call OpenAI API with image content.

    Args:
        model_name: Model name
        prompt: Text prompt
        image_data: Dict with 'data' (base64) and 'media_type'
        **kwargs: Extra parameters

    Returns:
        Model response text
    """
    from openai import OpenAI

    config = get_model_config(model_name)
    client = OpenAI(
        api_key=config["api_key"],
        base_url=config.get("base_url", "https://api.openai.com/v1")
    )

    content = [
        {"type": "image_url", "image_url": {"url": f"data:{image_data['media_type']};base64,{image_data['data']}"}},
        {"type": "text", "text": prompt}
    ]

    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "user", "content": content}],
        **kwargs
    )
    return response.choices[0].message.content


def _call_minimax_with_image(model_name: str, prompt: str, image_data: Dict[str, str], **kwargs) -> str:
    """
    Call Minimax API with image content.

    Args:
        model_name: Model name
        prompt: Text prompt
        image_data: Dict with 'data' (base64) and 'media_type'
        **kwargs: Extra parameters

    Returns:
        Model response text
    """
    import requests

    config = get_model_config(model_name)
    base_url = config.get("base_url", "https://api.minimaxi.com/anthropic")
    api_key = config["api_key"]

    content = [
        {"type": "image_url", "source": {"type": "base64", "media_type": image_data["media_type"], "data": image_data["data"]}},
        {"type": "text", "text": prompt}
    ]

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
            "messages": [{"role": "user", "content": content}]
        },
        timeout=kwargs.get("timeout", 120)
    )
    response.raise_for_status()
    response_json = response.json()

    for item in response_json.get("content", []):
        if item.get("type") == "text":
            return item.get("text", "")

    return response_json["content"][0].get("text", "")
```

Add to `PROVIDER_HANDLERS` dict in `client.py`:

```python
PROVIDER_HANDLERS_WITH_IMAGE = {
    "openai": _call_openai_with_image,
    "minimax": _call_minimax_with_image,
}
```

Add new function:

```python
def call_model_with_image(model_name: str, prompt: str, image_data: Dict[str, str], **kwargs) -> str:
    """
    Call model with image content.

    Args:
        model_name: Model name
        prompt: Text prompt
        image_data: Dict with 'data' (base64) and 'media_type'
        **kwargs: Extra parameters

    Returns:
        Model response text

    Raises:
        ValueError: If model doesn't support images
    """
    config = get_model_config(model_name)
    provider = config["provider"]

    handler = PROVIDER_HANDLERS_WITH_IMAGE.get(provider)
    if not handler:
        raise ValueError(f"模型 {model_name} 不支持图片输入")

    return handler(model_name, prompt, image_data, **kwargs)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_image_client.py::test_call_openai_with_image -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pg_semantic_operators/client.py
git commit -m "feat: add image support to OpenAI and Minimax providers

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: AI Image Operators

**Files:**
- Create: `pg_semantic_operators/operators/ai_image.py`
- Modify: `pg_semantic_operators/operators/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_image_operators.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pg_semantic_operators.operators.ai_image import ai_image_filter, ai_image_describe

def test_ai_image_filter_with_url():
    """Test ai_image_filter with URL"""
    # Use httpbin's test image
    result = ai_image_filter("gpt-4o", "https://httpbin.org/image/png", "a PNG image")
    assert result is True  # Should match since it's a PNG

def test_ai_image_describe_with_url():
    """Test ai_image_describe with URL"""
    result = ai_image_describe("gpt-4o", "https://httpbin.org/image/png")
    assert result is not None
    assert len(result) > 0

def test_ai_image_filter_unsupported_model():
    """Test error on unsupported model"""
    import pytest
    with pytest.raises(ValueError, match="不支持图片输入"):
        ai_image_filter("glm-4", "https://example.com/image.png", "a cat")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_image_operators.py -v
```
Expected: FAIL - module not found

- [ ] **Step 3: Write implementation**

```python
# pg_semantic_operators/operators/ai_image.py
"""AI Image operators for semantic filtering and description"""

from typing import Any
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
        raise  # Re-raise our own errors
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
        raise  # Re-raise our own errors
    except Exception as e:
        raise ValueError(f"图片描述失败: {e}") from e
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_image_operators.py -v
```
Expected: PASS

- [ ] **Step 5: Update __init__.py**

Modify `pg_semantic_operators/operators/__init__.py`:

```python
"""Semantic operators for PostgreSQL"""

from .ai_filter import ai_filter, AI_FILTER_SYSTEM_PROMPT
from .ai_query import ai_query, AI_QUERY_SYSTEM_PROMPT_BASE
from .ai_image import ai_image_filter, ai_image_describe

__all__ = [
    "ai_filter", "ai_query",
    "ai_image_filter", "ai_image_describe",
    "AI_FILTER_SYSTEM_PROMPT", "AI_QUERY_SYSTEM_PROMPT_BASE"
]
```

- [ ] **Step 6: Commit**

```bash
git add pg_semantic_operators/operators/ai_image.py pg_semantic_operators/operators/__init__.py
git commit -m "feat: add ai_image_filter and ai_image_describe operators

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: SQL Function Definitions

**Files:**
- Modify: `sql/pg_semantic_operators--1.0.sql`

- [ ] **Step 1: Add SQL function definitions**

Add to end of `sql/pg_semantic_operators--1.0.sql`:

```sql
-- ========== ai_image_filter ==========

CREATE OR REPLACE FUNCTION ai_image_filter(
    model_name TEXT,
    image_source TEXT,
    description TEXT
)
RETURNS BOOLEAN
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.ai_image import ai_image_filter
return ai_image_filter(model_name, image_source, description)
$$;

-- ========== ai_image_describe ==========

CREATE OR REPLACE FUNCTION ai_image_describe(
    model_name TEXT,
    image_source TEXT
)
RETURNS TEXT
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.ai_image import ai_image_describe
return ai_image_describe(model_name, image_source)
$$;

-- ========== 注释 ==========

COMMENT ON FUNCTION ai_image_filter(TEXT, TEXT, TEXT) IS
'判断图片是否符合描述。参数: model_name-模型名称, image_source-图片URL或本地路径, description-描述文本';
COMMENT ON FUNCTION ai_image_describe(TEXT, TEXT) IS
'生成图片描述。参数: model_name-模型名称, image_source-图片URL或本地路径';
```

- [ ] **Step 2: Commit**

```bash
git add sql/pg_semantic_operators--1.0.sql
git commit -m "feat: add SQL definitions for ai_image_filter and ai_image_describe

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Rebuild and Test in Docker

**Files:**
- Modify: `Dockerfile` (no changes needed, just rebuild)

- [ ] **Step 1: Rebuild Docker image**

```bash
docker compose down && docker compose up -d --build
```

- [ ] **Step 2: Test in PostgreSQL**

```bash
# Test ai_image_describe
docker exec pg_semantic psql -U postgres -d semantic_test -c "SELECT ai_image_describe('minimax', 'https://httpbin.org/image/png');"

# Test ai_image_filter
docker exec pg_semantic psql -U postgres -d semantic_test -c "SELECT ai_image_filter('minimax', 'https://httpbin.org/image/png', 'PNG 图片');"
```

- [ ] **Step 3: Verify output**

Expected: `ai_image_describe` returns a description, `ai_image_filter` returns `t` or `f`

- [ ] **Step 4: Commit Dockerfile changes (if any)**

If Dockerfile was modified (no changes expected for this task), commit:

```bash
git add Dockerfile
git commit -m "chore: rebuild to include image operators"
```

---

## Task 6: Update Operators Shim

**Files:**
- Modify: `pg_semantic_operators/operators.py`

- [ ] **Step 1: Update backward compatibility shim**

Replace current content:

```python
# Backward compatibility shim - imports from new modular structure
# This file is deprecated. Use: from pg_semantic_operators import ai_filter, ai_query

import warnings

from .operators.ai_filter import ai_filter
from .operators.ai_query import ai_query
from .operators.ai_image import ai_image_filter, ai_image_describe

warnings.warn(
    "Direct import from pg_semantic_operators.operators is deprecated. "
    "Use 'from pg_semantic_operators import ai_filter, ai_query, ai_image_filter, ai_image_describe' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["ai_filter", "ai_query", "ai_image_filter", "ai_image_describe"]
```

- [ ] **Step 2: Commit**

```bash
git add pg_semantic_operators/operators.py
git commit -m "feat: export image operators in backward compat shim

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Verification Checklist

After all tasks complete:

- [ ] `ai_image_filter('minimax', 'https://example.com/image.png', '描述')` returns boolean
- [ ] `ai_image_describe('minimax', 'https://example.com/image.png')` returns text
- [ ] Unsupported models (glm-4, etc.) raise `ValueError` with clear message
- [ ] Invalid URLs raise `ValueError` with "无法加载图片 URL"
- [ ] Missing local files raise `ValueError` with "本地图片文件不存在"
- [ ] All tests pass: `python -m pytest tests/ -v`