"""server.py —— WebSocket 服务端：接收录音，调用 Pipeline，返回对话响应"""
import asyncio
import uuid
from pathlib import Path

import websockets

from pipeline import process
from protocol import pack_message, unpack_message

TEMP_DIR = Path(__file__).parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)


async def handle_chat(websocket, header: dict, payload: bytes):
    request_id = header.get("request_id", "")

    # 录音保存为临时文件，交给 pipeline 处理
    input_path = TEMP_DIR / f"{request_id or uuid.uuid4().hex}.wav"
    input_path.write_bytes(payload)

    # 关键：pipeline 是同步阻塞的，丢到线程里跑，不卡住事件循环
    result = await asyncio.to_thread(process, str(input_path))

    reply_audio = Path(result["audio"]).read_bytes()
    await websocket.send(pack_message({
        "type": "chat_response",
        "request_id": request_id,
        "text": result["text"],
        "emotion": result["emotion"],
        "audio_format": "mp3",
    }, reply_audio))


async def handler(websocket):
    print(f"[连接] {websocket.remote_address}")
    try:
        async for frame in websocket:
            try:
                header, payload = unpack_message(frame)
                print(f"[请求] {header}")
                if header.get("type") == "chat_request":
                    await handle_chat(websocket, header, payload)
                else:
                    raise ValueError(f"未知消息类型：{header.get('type')}")
            except Exception as e:
                # 任何异常都按协议回 error 消息，不让服务崩掉（第 8 步再细化）
                await websocket.send(pack_message({
                    "type": "error",
                    "request_id": header.get("request_id", "") if "header" in dir() else "",
                    "code": "INTERNAL",
                    "message": str(e),
                }))
    finally:
        print(f"[断开] {websocket.remote_address}")


async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("Nagi 服务已启动：ws://localhost:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())