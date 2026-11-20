import asyncio

import edge_tts


async def main():
    tts = edge_tts.Communicate(
        text="你好,很高兴认识你，我是Nagi。",
        voice="zh-CN-XiaoxiaoNeural",
    )
    await tts.save("reply.mp3")


if __name__ == "__main__":
    asyncio.run(main())
    print("已生成 reply.mp3")