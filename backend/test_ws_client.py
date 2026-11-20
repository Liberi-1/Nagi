"""test_ws_client.py —— WebSocket 客户端，模拟将来的 Unity"""
import asyncio

import websockets


async def main():
    async with websockets.connect("ws://localhost:8765") as ws:
        print("已连接 Echo 服务，输入消息发送，输入 q 退出")
        while True:
            msg = input("你说：").strip()
            if msg.lower() == "q":
                break
            if not msg:
                continue
            await ws.send(msg)
            reply = await ws.recv()
            print(f"回声：{reply}")
            print("一致 ✅" if reply == msg else "不一致 ❌")


if __name__ == "__main__":
    asyncio.run(main())