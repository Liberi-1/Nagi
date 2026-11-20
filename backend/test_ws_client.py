"""test_ws_client.py —— 协议版客户端：模拟 Unity 发送录音，接收对话响应"""
import asyncio
import uuid
from pathlib import Path

import websockets

from protocol import pack_message, unpack_message

INPUT_WAV = Path(__file__).parent / "input.wav"
REPLY_MP3 = Path(__file__).parent / "reply_ws.mp3"


async def main():
    audio_bytes = INPUT_WAV.read_bytes()
    header = {
        "type": "chat_request",
        "request_id": uuid.uuid4().hex[:8],
        "audio_format": "wav",
        "sample_rate": 16000,
    }

    async with websockets.connect("ws://localhost:8765") as ws:
        await ws.send(pack_message(header, audio_bytes))
        print(f"[已发送] 录音 {len(audio_bytes)} 字节，等待回复……")

        frame = await ws.recv()
        resp_header, resp_payload = unpack_message(frame)

        if resp_header.get("type") == "chat_response":
            print(f"[回复文本] {resp_header['text']}")
            print(f"[情绪标签] {resp_header['emotion']}")
            REPLY_MP3.write_bytes(resp_payload)
            print(f"[回复音频] 已保存为 {REPLY_MP3.name}（{len(resp_payload)} 字节）")
        else:
            print(f"[错误] {resp_header.get('code')}：{resp_header.get('message')}")


if __name__ == "__main__":
    asyncio.run(main())