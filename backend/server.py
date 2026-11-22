"""server.py —— WebSocket 服务：连接级会话 + 对话响应 + 分层错误"""
import asyncio
import struct
import uuid
from pathlib import Path

import websockets

from pipeline import StageError, process
from protocol import pack_message, unpack_message

TEMP_DIR = Path(__file__).parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)

PIPELINE_TIMEOUT = 60  # 单次对话处理最多 60 秒


async def send_error(
    websocket,
    request_id: str,
    code: str,
    message: str,
):
    """按协议回 error 消息，服务本身不崩。"""
    print(f"[错误] {code}：{message}")

    await websocket.send(pack_message({
        "type": "error",
        "request_id": request_id,
        "code": code,
        "message": message,
    }))


async def handle_chat(
    websocket,
    header: dict,
    payload: bytes,
    session_id: str,
):
    request_id = str(
        header.get("request_id") or uuid.uuid4().hex
    )

    # 文件名使用服务端生成的 UUID，不直接使用客户端传入的 request_id
    input_path = TEMP_DIR / f"{uuid.uuid4().hex}.wav"
    input_path.write_bytes(payload)

    # 线程里跑同步管线，外套超时
    result = await asyncio.wait_for(
        asyncio.to_thread(
            process,
            str(input_path),
            session_id=session_id,
            request_id=request_id,
        ),
        timeout=PIPELINE_TIMEOUT,
    )

    reply_audio = Path(result["audio"]).read_bytes()

    await websocket.send(pack_message({
        "type": "chat_response",
        "request_id": request_id,
        "session_id": result["session_id"],
        "text": result["text"],
        "emotion": result["emotion"],
        "audio_format": "mp3",
    }, reply_audio))


async def handler(websocket):
    # 同一连接内的所有请求共享 session_id
    session_id = uuid.uuid4().hex

    print(
        f"[连接] {websocket.remote_address}，"
        f"session={session_id}"
    )

    try:
        async for frame in websocket:
            request_id = ""

            try:
                header, payload = unpack_message(frame)
                request_id = str(header.get("request_id", ""))

                print(
                    f"[请求] session={session_id}，"
                    f"header={header}"
                )

                if header.get("type") != "chat_request":
                    raise ValueError(
                        f"未知消息类型：{header.get('type')}"
                    )

                await handle_chat(
                    websocket,
                    header,
                    payload,
                    session_id,
                )

            except StageError as e:
                await send_error(
                    websocket,
                    request_id,
                    f"{e.stage}_FAILED",
                    str(e.cause),
                )
            except (asyncio.TimeoutError, TimeoutError):
                await send_error(
                    websocket,
                    request_id,
                    "TIMEOUT",
                    f"处理超过 {PIPELINE_TIMEOUT} 秒，已放弃",
                )
            except (ValueError, struct.error) as e:
                await send_error(
                    websocket,
                    request_id,
                    "BAD_REQUEST",
                    str(e),
                )
            except Exception as e:
                await send_error(
                    websocket,
                    request_id,
                    "INTERNAL",
                    str(e),
                )
    finally:
        print(
            f"[断开] {websocket.remote_address}，"
            f"session={session_id}"
        )


async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("Nagi 服务已启动：ws://localhost:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())