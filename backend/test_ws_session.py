"""test_ws_session.py —— 验证 WebSocket 连接级 session_id"""
import asyncio
import uuid
from pathlib import Path
from unittest.mock import patch

import websockets

import server
from protocol import pack_message, unpack_message

calls = []


def fake_process(audio_path, *, session_id, request_id):
    """模拟 Pipeline，避免测试依赖 ASR、LLM、TTS 和外部网络。"""
    input_path = Path(audio_path)
    payload = input_path.read_bytes()

    output_path = input_path.with_suffix(".mp3")
    output_path.write_bytes(b"fake-" + payload)

    calls.append({
        "session_id": session_id,
        "request_id": request_id,
        "input_path": input_path,
        "output_path": output_path,
    })

    return {
        "text": f"模拟回复：{request_id}",
        "audio": output_path,
        "emotion": "neutral",
        "session_id": session_id,
        "request_id": request_id,
    }


async def send_request(websocket, request_id, payload):
    header = {
        "type": "chat_request",
        "request_id": request_id,
        "audio_format": "wav",
        "sample_rate": 16000,
    }

    await websocket.send(pack_message(header, payload))
    frame = await websocket.recv()

    return unpack_message(frame)


async def main() -> None:
    try:
        with patch("server.process", side_effect=fake_process):
            async with websockets.serve(
                server.handler,
                "localhost",
                8766,
            ):
                uri = "ws://localhost:8766"

                # 第一个连接连续发送两轮请求
                async with websockets.connect(uri) as ws:
                    first_header, first_audio = await send_request(
                        ws,
                        "request-1",
                        b"first",
                    )
                    second_header, second_audio = await send_request(
                        ws,
                        "request-2",
                        b"second",
                    )

                # 新建连接，发送第三轮请求
                async with websockets.connect(uri) as ws:
                    third_header, third_audio = await send_request(
                        ws,
                        "request-3",
                        b"third",
                    )

        # 同一连接的两轮共享 session_id
        assert first_header["session_id"] == second_header["session_id"]

        # 新连接必须使用新的 session_id
        assert third_header["session_id"] != first_header["session_id"]

        # 请求 ID 应正确配对
        assert first_header["request_id"] == "request-1"
        assert second_header["request_id"] == "request-2"
        assert third_header["request_id"] == "request-3"

        # 音频负载应原样从模拟 Pipeline 返回
        assert first_audio == b"fake-first"
        assert second_audio == b"fake-second"
        assert third_audio == b"fake-third"

        print("[通过] 同一连接的多轮请求共享 session_id")
        print("[通过] 新连接会创建新的 session_id")
        print("[通过] request_id 和二进制音频响应正常")

    finally:
        for call in calls:
            call["input_path"].unlink(missing_ok=True)
            call["output_path"].unlink(missing_ok=True)

        print("[清理] WebSocket 测试文件已删除")


if __name__ == "__main__":
    asyncio.run(main())