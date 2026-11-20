"""asr.py —— ASR 模块：音频文件 → 文本"""
import whisper

MODEL_NAME = "base"
_model = None


def _get_model():
    """模型懒加载：第一次用时才载入，之后复用。"""
    global _model
    if _model is None:
        _model = whisper.load_model(MODEL_NAME, device="cpu")
    return _model


def transcribe(audio_path: str) -> str:
    """识别音频文件，返回文本。"""
    result = _get_model().transcribe(audio_path, language="zh", fp16=False)
    return result["text"].strip()