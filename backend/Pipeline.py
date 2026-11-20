"""pipeline.py —— 对话管线：音频进，回复文本 + 音频出"""
from pathlib import Path

from asr import transcribe
from llm import chat
from tts import speak

OUTPUT_AUDIO = Path(__file__).parent / "reply.mp3"


def process(audio_path: str) -> dict:
    """完整跑一轮对话：录音 → 识别 → 回复 → 合成。"""
    user_text = transcribe(audio_path)
    print(f"[ASR] 识别结果：{user_text}")

    reply_text = chat(user_text)
    print(f"[LLM] 回复：{reply_text}")

    audio_out = speak(reply_text, OUTPUT_AUDIO)
    print(f"[TTS] 已生成：{audio_out}")

    return {
        "text": reply_text,
        "audio": audio_out,
        "emotion": "neutral",   # v0.1 固定 neutral，v0.3 再接情绪
    }