# AI Audio Operators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `ai_audio_filter` and `ai_audio_describe` operators that transcribe or semantically filter audio using GPT-4o's audio input capability.

**Architecture:** New `ai_audio.py` and `ai_audio_helpers.py` modules mirror the existing `ai_image.py` / `ai_image_helpers.py` pattern. `client.py` gets a new `_call_openai_with_audio` function registered in `PROVIDER_HANDLERS_WITH_AUDIO`. Only OpenAI (`gpt-4o-audio-preview`) is supported.

**Tech Stack:** PostgreSQL plpython3u, OpenAI SDK, `requests` library (already available), base64 encoding.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `pg_semantic_operators/operators/ai_audio_helpers.py` | Create | Load audio from URL/local file, detect media type, return base64 dict |
| `pg_semantic_operators/operators/ai_audio.py` | Create | `ai_audio_filter` and `ai_audio_describe` using `call_model_with_audio` |
| `pg_semantic_operators/client.py` | Modify | Add `_call_openai_with_audio`, add to `PROVIDER_HANDLERS_WITH_AUDIO` |
| `pg_semantic_operators/operators/__init__.py` | Modify | Export `ai_audio_filter`, `ai_audio_describe` |
| `pg_semantic_operators/operators.py` | Modify | Backward compat shim exports audio operators |
| `pg_semantic_operators/__init__.py` | Modify | Main module exports audio operators |
| `sql/pg_semantic_operators--1.0.sql` | Modify | Add `ai_audio_filter` and `ai_audio_describe` SQL function definitions |

---

## Task 1: Create ai_audio_helpers.py

**Files:**
- Create: `pg_semantic_operators/operators/ai_audio_helpers.py`

- [ ] **Step 1: Write the audio helper module**

```python
"""Audio loading utilities for AI audio operators"""

import base64
import os
from typing import Dict
import requests


def load_audio(source: str) -> Dict[str, str]:
    """
    Load an audio file from URL or local path.

    Args:
        source: Audio URL (http:// or https://) or local file path

    Returns:
        Dict with 'data' (base64 encoded audio) and 'media_type'

    Raises:
        ValueError: If audio cannot be loaded
    """
    if source.startswith(("http://", "https://")):
        return _load_from_url(source)
    else:
        return _load_from_file(source)


def _load_from_url(url: str) -> Dict[str, str]:
    """Load audio from URL"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"无法加载音频 URL: {url}") from e

    content = response.content
    media_type = _detect_media_type(content, url)
    if not media_type.startswith("audio/"):
        ext = os.path.splitext(url)[1].lower()
        raise ValueError(f"不支持的音频格式: {ext}")

    encoded = base64.b64encode(content).decode("utf-8")
    return {"data": encoded, "media_type": media_type}


def _load_from_file(path: str) -> Dict[str, str]:
    """Load audio from local file"""
    if not os.path.exists(path):
        raise ValueError(f"本地音频文件不存在: {path}")

    with open(path, "rb") as f:
        content = f.read()

    media_type = _detect_media_type(content, path)
    if not media_type.startswith("audio/"):
        ext = os.path.splitext(path)[1].lower()
        raise ValueError(f"不支持的音频格式: {ext}")

    encoded = base64.b64encode(content).decode("utf-8")
    return {"data": encoded, "media_type": media_type}


def _detect_media_type(content: bytes, source: str) -> str:
    """Detect media type from content or file extension"""
    # Check common audio magic bytes
    if content[:4] == b"ID3" or (content[:3] == b"\xff\xfb" or content[:3] == b"\xff\xf3" or content[:3] == b"\xff\xf2"):
        return "audio/mpeg"
    if content[:4] == b"RIFF" and b"WAVE" in content[:12]:
        return "audio/wav"
    if content[:4] == b"RIFF" and b"WEBP" in content[:12]:
        # Could be webm audio
        return "audio/webm"
    if content[:4] == b"OggS":
        return "audio/ogg"
    if content[:4] == b"ftyp" and b"M4A" in content[:12]:
        return "audio/mp4"
    if content[:4] == b"\x00\x00\x00":
        # Check for 3gpp
        return "audio/3gpp"

    # Fallback to extension
    ext = os.path.splitext(source)[1].lower()
    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
        ".3gp": "audio/3gpp",
    }
    return mime_map.get(ext, "application/octet-stream")
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile pg_semantic_operators/operators/ai_audio_helpers.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add pg_semantic_operators/operators/ai_audio_helpers.py
git commit -m "feat: add audio loading helpers for AI audio operators"
```

---

## Task 2: Create ai_audio.py

**Files:**
- Create: `pg_semantic_operators/operators/ai_audio.py`

- [ ] **Step 1: Write the audio operators module**

```python
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
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile pg_semantic_operators/operators/ai_audio.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add pg_semantic_operators/operators/ai_audio.py
git commit -m "feat: add ai_audio_filter and ai_audio_describe operators"
```

---

## Task 3: Add _call_openai_with_audio to client.py

**Files:**
- Modify: `pg_semantic_operators/client.py:149-196` (after existing `_call_minimax_with_image`)

- [ ] **Step 1: Add the `_call_openai_with_audio` function and register it**

Add the following function after `_call_minimax_with_image` (around line 197):

```python
def _call_openai_with_audio(model_name: str, prompt: str, audio_data: Dict[str, str], **kwargs) -> str:
    from openai import OpenAI
    config = get_model_config(model_name)
    client = OpenAI(
        api_key=config["api_key"],
        base_url=config.get("base_url", "https://api.openai.com/v1")
    )
    content = [
        {
            "type": "audio",
            "source": {
                "type": "base64",
                "media_type": audio_data["media_type"],
                "data": audio_data["data"]
            }
        },
        {"type": "text", "text": prompt}
    ]
    response = client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "user", "content": content}],
        **kwargs
    )
    return response.choices[0].message.content
```

Then update `PROVIDER_HANDLERS_WITH_AUDIO` dict to:

```python
PROVIDER_HANDLERS_WITH_AUDIO = {
    "openai": _call_openai_with_audio,
    "minimax": _call_minimax_with_image,  # Keep for image compatibility
}
```

And add new dict:

```python
PROVIDER_HANDLERS_WITH_AUDIO_ONLY = {
    "openai": _call_openai_with_audio,
}
```

Add new function after `call_model_with_image`:

```python
def call_model_with_audio(model_name: str, prompt: str, audio_data: Dict[str, str], **kwargs) -> str:
    config = get_model_config(model_name)
    provider = config["provider"]
    handler = PROVIDER_HANDLERS_WITH_AUDIO_ONLY.get(provider)
    if not handler:
        raise ValueError(f"模型 {model_name} 不支持音频输入")
    return handler(model_name, prompt, audio_data, **kwargs)
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile pg_semantic_operators/client.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add pg_semantic_operators/client.py
git commit -m "feat: add call_model_with_audio and _call_openai_with_audio"
```

---

## Task 4: Update operators/__init__.py

**Files:**
- Modify: `pg_semantic_operators/operators/__init__.py`

- [ ] **Step 1: Add audio exports**

Change:
```python
from .ai_image import ai_image_filter, ai_image_describe
```
To:
```python
from .ai_image import ai_image_filter, ai_image_describe
from .ai_audio import ai_audio_filter, ai_audio_describe
```

Change `__all__` from:
```python
__all__ = [
    "ai_filter", "ai_query",
    "ai_image_filter", "ai_image_describe",
    "AI_FILTER_SYSTEM_PROMPT", "AI_QUERY_SYSTEM_PROMPT_BASE"
]
```
To:
```python
__all__ = [
    "ai_filter", "ai_query",
    "ai_image_filter", "ai_image_describe",
    "ai_audio_filter", "ai_audio_describe",
    "AI_FILTER_SYSTEM_PROMPT", "AI_QUERY_SYSTEM_PROMPT_BASE"
]
```

- [ ] **Step 2: Commit**

```bash
git add pg_semantic_operators/operators/__init__.py
git commit -m "feat: export ai_audio_filter and ai_audio_describe"
```

---

## Task 5: Update operators.py (backward compat shim)

**Files:**
- Modify: `pg_semantic_operators/operators.py`

- [ ] **Step 1: Add audio imports to shim**

Change:
```python
from .operators.ai_image import ai_image_filter, ai_image_describe
```
To:
```python
from .operators.ai_image import ai_image_filter, ai_image_describe
from .operators.ai_audio import ai_audio_filter, ai_audio_describe
```

Change `__all__` from:
```python
__all__ = ["ai_filter", "ai_query", "ai_image_filter", "ai_image_describe"]
```
To:
```python
__all__ = ["ai_filter", "ai_query", "ai_image_filter", "ai_image_describe", "ai_audio_filter", "ai_audio_describe"]
```

- [ ] **Step 2: Commit**

```bash
git add pg_semantic_operators/operators.py
git commit -m "feat: add audio operators to backward compat shim"
```

---

## Task 6: Update __init__.py

**Files:**
- Modify: `pg_semantic_operators/__init__.py`

- [ ] **Step 1: Add audio exports to main module**

Update the `from .operators import` line:
```python
from .operators import ai_query, ai_filter, ai_image_filter, ai_image_describe, ai_audio_filter, ai_audio_describe
```

Update `__all__`:
```python
__all__ = [
    "ai_query", "ai_filter",
    "ai_image_filter", "ai_image_describe",
    "ai_audio_filter", "ai_audio_describe",
    "get_model_config", "list_models", "call_model",
    "AI_FILTER_SYSTEM_PROMPT", "AI_QUERY_SYSTEM_PROMPT_BASE"
]
```

- [ ] **Step 2: Commit**

```bash
git add pg_semantic_operators/__init__.py
git commit -m "feat: export audio operators from main module"
```

---

## Task 7: Add SQL function definitions

**Files:**
- Modify: `sql/pg_semantic_operators--1.0.sql`

- [ ] **Step 1: Add SQL function definitions**

Add after the existing `ai_image_describe` function (after line 148):

```sql
-- ========== ai_audio_filter ==========

CREATE OR REPLACE FUNCTION ai_audio_filter(
    model_name TEXT,
    audio_source TEXT,
    description TEXT
)
RETURNS BOOLEAN
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.ai_audio import ai_audio_filter
return ai_audio_filter(model_name, audio_source, description)
$$;

-- ========== ai_audio_describe ==========

CREATE OR REPLACE FUNCTION ai_audio_describe(
    model_name TEXT,
    audio_source TEXT
)
RETURNS TEXT
LANGUAGE plpython3u
AS $$
from pg_semantic_operators.operators.ai_audio import ai_audio_describe
return ai_audio_describe(model_name, audio_source)
$$;

-- ========== 注释 ==========

COMMENT ON FUNCTION ai_audio_filter(TEXT, TEXT, TEXT) IS
'判断音频是否符合描述。参数: model_name-模型名称, audio_source-音频URL或本地路径, description-描述文本';
COMMENT ON FUNCTION ai_audio_describe(TEXT, TEXT) IS
'生成音频描述/转写。参数: model_name-模型名称, audio_source-音频URL或本地路径';
```

- [ ] **Step 2: Commit**

```bash
git add sql/pg_semantic_operators--1.0.sql
git commit -m "feat: add SQL definitions for ai_audio_filter and ai_audio_describe"
```

---

## Verification

After all tasks complete, verify the SQL file contains the new functions:

```bash
grep -n "ai_audio" sql/pg_semantic_operators--1.0.sql
```

Expected output: lines for `ai_audio_filter`, `ai_audio_describe`, and their comments.

---

## Spec Coverage Check

- [x] `ai_audio_filter(model_name, audio_source, description) -> bool` — Task 2
- [x] `ai_audio_describe(model_name, audio_source) -> str` — Task 2
- [x] Audio source URL handling — Task 1 (`_load_from_url`)
- [x] Audio source local file handling — Task 1 (`_load_from_file`)
- [x] Media type detection — Task 1 (`_detect_media_type`)
- [x] OpenAI audio content block format — Task 3 (`_call_openai_with_audio`)
- [x] Error messages in Chinese — Task 1 & 2
- [x] SQL interface — Task 7
- [x] Module exports (operators, shim, main) — Tasks 4, 5, 6
