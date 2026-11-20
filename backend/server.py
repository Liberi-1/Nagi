"""server.py —— WebSocket 服务端（当前为 Echo 模式）"""
import asyncio

import websockets


async def handler(websocket):
    """每有一个客户端连上来，就运行一次这个函数。"""
    print(f"[连接] 客户端接入：{websocket.remote_address}")
    try:
        async for message in websocket:      # 持续收消息，直到对方断开
            print(f"[收到] {message}")
            await websocket.send(message)     # 原样返回（Echo）
    finally:
        print(f"[断开] {websocket.remote_address}")


async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("Echo 服务已启动：ws://localhost:8765")
        await asyncio.Future()                # 永久运行，Ctrl+C 停止


if __name__ == "__main__":
    asyncio.run(main())