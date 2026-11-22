"""pipeline.py —— 对话管线：音频进，回复文本 + 音频出（含阶段错误与重试）"""
import time
from pathlib import Path

from asr import transcribe
from llm import chat
from tts import speak

OUTPUT_AUDIO = Path(__file__).parent / "reply.mp3"


class StageError(Exception):
    """带阶段信息的管线错误，stage 为 ASR / LLM / TTS。"""

    def __init__(self, stage: str, cause: Exception):
        self.stage = stage
        self.cause = cause
        super().__init__(f"{stage} 阶段失败：{cause}")


def with_retry(func, *args, max_attempts: int = 3, **kwargs):
    """网络操作有限重试：失败后等 1s、2s 再试，最多 3 次，仍失败则抛出。"""
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_attempts:
                raise
            print(f"[重试] {func.__name__} 第 {attempt} 次失败（{e}），稍后重试")
            time.sleep(attempt)


def process(audio_path: str) -> dict:
    """完整跑一轮对话：录音 → 识别 → 回复 → 合成。"""
    try:
        user_text = transcribe(audio_path)
    except Exception as e:
        raise StageError("ASR", e)
    if not user_text:
        raise StageError("ASR", ValueError("没有识别出内容，可能是空录音或噪音"))
    print(f"[ASR] 识别结果：{user_text}")

    try:
        reply_text = with_retry(chat, user_text)      # LLM 走网络，可重试
    except Exception as e:
        raise StageError("LLM", e)
    print(f"[LLM] 回复：{reply_text}")

    try:
        audio_out = with_retry(speak, reply_text, OUTPUT_AUDIO)  # TTS 走网络，可重试
    except Exception as e:
        raise StageError("TTS", e)
    print(f"[TTS] 已生成：{audio_out}")

    return {"text": reply_text, "audio": audio_out, "emotion": "neutral"}