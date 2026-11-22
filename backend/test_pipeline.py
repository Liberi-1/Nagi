"""test_pipeline.py —— 第 4 步验证：一次运行，音频进、音频出"""
import sys
import time

from pipeline import process


def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "input.wav"

    start = time.time()
    result = process(audio_path)
    elapsed = time.time() - start

    print("-" * 40)
    print("回复文本：", result["text"])
    print("回复音频：", result["audio"])
    print("情绪标签：", result["emotion"])
    print(f"总耗时：{elapsed:.1f} 秒")


if __name__ == "__main__":
    main()