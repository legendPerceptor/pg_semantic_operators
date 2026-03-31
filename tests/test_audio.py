#!/usr/bin/env python3
"""
测试 ai_audio_describe 和 ai_audio_filter 算子

测试流程：
1. 用 Minimax TTS 生成中文测试音频
2. 用 ai_audio_describe 转写
3. 用 ai_audio_filter 判断语言

需要设置环境变量：
- MINIMAX_API_KEY: Minimax TTS API Key
- OPENAI_API_KEY: OpenAI API Key (已在 models.json 中配置)
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from pg_semantic_operators.operators.ai_audio_helpers import load_audio
from pg_semantic_operators.client import call_model_with_audio

MODEL_NAME = "gpt-4o-audio-preview"


def generate_audio_minimax(text: str, output_path: str = "/tmp/test_audio.mp3") -> str:
    """用 Minimax TTS 生成音频"""
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        raise ValueError("需要设置 MINIMAX_API_KEY 环境变量")

    print(f"[TTS] 生成音频: {text[:30]}...")

    response = requests.post(
        "https://api.minimaxi.com/v1/t2a_v2",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "speech-2.8-hd",
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": "male-qn-qingse",
                "speed": 1,
                "emotion": "happy"
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3"
            },
            "output_format": "url"
        },
        timeout=30
    )
    response.raise_for_status()
    data = response.json()

    audio_url = data.get("data", {}).get("audio", "")
    if not audio_url:
        raise Exception(f"TTS 返回无效: {data}")

    # 下载音频
    audio_response = requests.get(audio_url, timeout=30)
    audio_response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(audio_response.content)

    print(f"[TTS] 音频已保存: {output_path} ({len(audio_response.content)} bytes)")
    return output_path


def test_audio_describe(audio_path: str):
    """测试 ai_audio_describe"""
    print(f"\n[TEST] ai_audio_describe")
    print("-" * 40)

    try:
        audio_data = load_audio(audio_path)
        print(f"[INFO] 音频格式: {audio_data['media_type']}")
        print(f"[INFO] 音频大小: {len(audio_data['data'])} bytes (base64)")

        prompt = "请详细描述这段音频的内容，包括语言、说话人数量、主题等细节。"
        result = call_model_with_audio(MODEL_NAME, prompt, audio_data)

        print(f"[RESULT] {result}")
        return result

    except Exception as e:
        print(f"[ERROR] {e}")
        return None


def test_audio_filter(audio_path: str, description: str):
    """测试 ai_audio_filter"""
    print(f"\n[TEST] ai_audio_filter (描述: {description})")
    print("-" * 40)

    try:
        from pg_semantic_operators.operators.ai_audio import ai_audio_filter
        result = ai_audio_filter(MODEL_NAME, audio_path, description)

        print(f"[RESULT] {result}")
        return result

    except Exception as e:
        print(f"[ERROR] {e}")
        return None


def main():
    print("=" * 50)
    print("AI Audio 算子测试")
    print("=" * 50)

    # 测试文本
    test_text = "下午好！我们都是最棒的！欢迎使用语音转文字功能。"

    # 1. 生成测试音频
    audio_path = generate_audio_minimax(test_text)

    # 2. 测试 ai_audio_describe
    test_audio_describe(audio_path)

    # 3. 测试 ai_audio_filter - 判断是否包含中文
    result_zh = test_audio_filter(audio_path, "中文")
    print(f"\n[验证] 是否为中文: {result_zh} (期望: True)")

    # 4. 测试 ai_audio_filter - 判断是否包含英文
    result_en = test_audio_filter(audio_path, "英文")
    print(f"[验证] 是否为英文: {result_en} (期望: False)")

    # 5. 测试 ai_audio_filter - 判断是否包含"天气"
    result_weather = test_audio_filter(audio_path, "天气")
    print(f"[验证] 是否包含天气: {result_weather} (期望: False)")

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
