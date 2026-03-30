# AI Image Operators Design

## Overview

Add image semantic filtering and description capabilities to pg_semantic_operators. Users can pass an image URL or local file path, along with a natural language description, and the model will judge if the image matches the description.

## Functions

### ai_image_filter(model_name, image_source, description) → boolean

Judge if an image matches a semantic description.

**Parameters:**
- `model_name`: Model name (e.g., "gpt-4o", "minimax")
- `image_source`: Image URL (http:// or https://) or local file path
- `description`: Natural language description to judge against

**Returns:** `true` if image matches description, `false` otherwise

**Raises:** `ValueError` with clear message if image can't be loaded or model doesn't support vision

### ai_image_describe(model_name, image_source) → text

Generate a natural language description of an image.

**Parameters:**
- `model_name`: Model name (e.g., "gpt-4o", "minimax")
- `image_source`: Image URL (http:// or https://) or local file path

**Returns:** Text description of the image

**Raises:** `ValueError` with clear message if image can't be loaded or model doesn't support vision

## Image Source Handling

| Source Type | Detection | Handling |
|-------------|-----------|----------|
| URL | Starts with `http://` or `https://` | Fetch content, encode as base64 |
| Local file | Otherwise | Read file, encode as base64 |

**Error cases:**

| Error | Message |
|-------|---------|
| Invalid URL | `"无法加载图片 URL: {url}"` |
| Local file not found | `"本地图片文件不存在: {path}"` |
| Model doesn't support vision | `"模型 {model} 不支持图片输入"` |
| Network error | `"图片加载失败: {reason}"` |

## Model Support

### GPT-4o (OpenAI)
- Provider: openai
- Use `gpt-4o` model which supports vision
- Content format: OpenAI chat completions with image content blocks

### Minimax
- Provider: minimax
- Model: `MiniMax-M2.7` or vision-capable variant
- Use Minimax's Anthropic-compatible API with image content

## SQL Interface

```sql
-- Filter images by description
SELECT * FROM images
WHERE ai_image_filter('gpt-4o', url, '产品照片') = true;

-- Describe an image
SELECT ai_image_describe('gpt-4o', '/path/to/image.jpg');
```

## File Structure

```
pg_semantic_operators/
├── pg_semantic_operators/
│   ├── operators/
│   │   ├── ai_image.py        # New: image operators
│   │   ├── ai_filter.py
│   │   └── ai_query.py
│   ├── client.py              # Modify: add _call_*_with_image support
│   └── config.py
└── sql/
    └── pg_semantic_operators--1.0.sql  # Modify: add new function definitions
```

## Implementation Steps

1. **client.py**: Modify `_call_openai` and `_call_minimax` to support image content blocks
2. **ai_image.py**: Create new module with `ai_image_filter` and `ai_image_describe` functions
3. **__init__.py**: Export new functions
4. **operators.py**: Re-export for backward compatibility
5. **SQL**: Add `CREATE FUNCTION` statements for both new functions
6. **Dockerfile**: Rebuild with new code

## Dependencies

- `requests` library (already installed) — for fetching URL images
- No new Python packages required