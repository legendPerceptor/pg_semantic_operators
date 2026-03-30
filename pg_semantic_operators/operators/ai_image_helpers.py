"""Image loading utilities for AI image operators"""

import base64
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
