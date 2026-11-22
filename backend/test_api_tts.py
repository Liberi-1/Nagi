"""test_api_tts.py —— 验证 TTS 预览接口返回真实 MP3"""
import json
import urllib.request


def main() -> None:
    payload = json.dumps({
        "text": "你好，我是 Nagi，这是一条音色试听。",
        "voice": "zh-CN-XiaoxiaoNeural",
    }, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(
        "http://127.0.0.1:8000/api/tts/preview",
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=60,
    ) as response:
        audio = response.read()

        assert response.status == 200
        assert response.headers.get_content_type() == "audio/mpeg"
        assert len(audio) > 1000, "返回的音频数据异常短"

    print(f"[通过] 已返回真实 MP3，大小为 {len(audio)} 字节")


if __name__ == "__main__":
    main()