"""tts.py —— TTS 模块：回复文本 → 音频文件"""
import asyncio
from pathlib import Path

import edge_tts

VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_OUTPUT = Path(__file__).parent / "reply.mp3"


async def _synthesize(
    text: str,
    output_path: Path,
    voice: str,
) -> None:
    communicate = edge_tts.Communicate(
        text,
        voice,
    )
    await communicate.save(str(output_path))


def speak(
    text: str,
    output_path: Path = DEFAULT_OUTPUT,
    voice: str = VOICE,
) -> Path:
    """把文本合成为音频文件，可选择音色并返回文件路径。"""
    asyncio.run(_synthesize(
        text,
        output_path,
        voice,
    ))
    return output_path