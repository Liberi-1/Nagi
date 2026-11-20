"""test_ws_client.py —— 协议版客户端；加 bad 参数可发送垃圾帧测试错误处理"""
import asyncio
import sys
import uuid
from pathlib import Path

import websockets

from protocol import pack_message, unpack_message

INPUT_WAV = Path(__file__).parent / "input.wav"
REPLY_MP3 = Path(__file__).parent / "reply_ws.mp3"


async def main():
    async with websockets.connect("ws://localhost:8765") as ws:
        if len(sys.argv) > 1 and sys.argv[1] == "bad":
            await ws.send(b"garbage")          # 故意发不合法的数据
            print("[已发送] 垃圾帧（测试错误处理）")
        else:
            header = {
                "type": "chat_request",
                "request_id": uuid.uuid4().hex[:8],
                "audio_format": "wav",
                "sample_rate": 16000,
            }
            await ws.send(pack_message(header, INPUT_WAV.read_bytes()))
            print("[已发送] 录音，等待回复……")

        frame = await ws.recv()
        resp_header, resp_payload = unpack_message(frame)

        if resp_header.get("type") == "chat_response":
            print(f"[回复文本] {resp_header['text']}")
            print(f"[情绪标签] {resp_header['emotion']}")
            REPLY_MP3.write_bytes(resp_payload)
            print(f"[回复音频] 已保存为 {REPLY_MP3.name}")
        else:
            print(f"[错误] {resp_header.get('code')}：{resp_header.get('message')}")


if __name__ == "__main__":
    asyncio.run(main())