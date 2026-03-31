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
        return "audio/webm"
    if content[:4] == b"OggS":
        return "audio/ogg"
    if content[:4] == b"ftyp" and b"M4A" in content[:12]:
        return "audio/mp4"
    if content[:4] == b"\x00\x00\x00":
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
