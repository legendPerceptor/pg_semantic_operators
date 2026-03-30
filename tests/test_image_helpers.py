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