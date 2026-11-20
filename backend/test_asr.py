"""test_asr.py —— Whisper 单点验证：本地 WAV → 中文文本"""
import time

import whisper

MODEL_NAME = "base"        # 多语言 base 模型，首次运行自动下载（约 140 MB）
AUDIO_PATH = "input.wav"


def main():
    print(f"加载模型 {MODEL_NAME}（CPU）……")
    model = whisper.load_model(MODEL_NAME, device="cpu")

    print(f"识别 {AUDIO_PATH} ……")
    start = time.time()
    result = model.transcribe(
    AUDIO_PATH,
    language="zh",
    fp16=False,
    initial_prompt="以下是中文对话，对话中的角色名叫 Nagi。",
    )
    elapsed = time.time() - start

    print("-" * 40)
    print("识别结果：", result["text"].strip())
    print(f"耗时：{elapsed:.1f} 秒")
    print("-" * 40)


if __name__ == "__main__":
    main()