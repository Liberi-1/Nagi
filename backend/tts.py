"""tts.py —— TTS 模块：回复文本 → 音频文件"""
import asyncio
from pathlib import Path

import edge_tts

VOICE = "zh-CN-XiaoxiaoNeural"   # 中文女声，音色后面可以换
DEFAULT_OUTPUT = Path(__file__).parent / "reply.mp3"


async def _synthesize(text: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(output_path))


def speak(text: str, output_path: Path = DEFAULT_OUTPUT) -> Path:
    """把文本合成为音频文件，返回文件路径。"""
    asyncio.run(_synthesize(text, output_path))
    return output_path