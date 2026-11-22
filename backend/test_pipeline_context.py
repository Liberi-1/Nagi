"""test_pipeline_context.py —— 不依赖真实 ASR/TTS 的 Pipeline 数据层测试"""
import uuid
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select

from database import SessionLocal
from models import ConversationRecord
from pipeline import process
from repositories import get_default_user, get_recent_conversations

chat_calls = []
audio_paths = []


def fake_chat(user_text, persona_content=None, history=None):
    """模拟 LLM，并记录 Pipeline 实际传入的人设和历史。"""
    chat_calls.append({
        "user_text": user_text,
        "persona_content": persona_content,
        "history": list(history or []),
    })

    return f"{user_text}的模拟回复"


def fake_speak(text, output_path):
    """模拟 TTS，只生成一个占位音频文件，不访问网络。"""
    output_path = Path(output_path)
    output_path.write_bytes(b"fake mp3 for pipeline test")
    return output_path


def main() -> None:
    session_id = f"test-pipeline-{uuid.uuid4().hex}"

    try:
        with (
            patch(
                "pipeline.transcribe",
                side_effect=["第一轮输入", "第二轮输入"],
            ),
            patch("pipeline.chat", side_effect=fake_chat),
            patch("pipeline.speak", side_effect=fake_speak),
        ):
            first = process(
                "不存在的音频也能测试，因为 ASR 已被模拟.wav",
                session_id=session_id,
                request_id="test-request-1",
            )
            audio_paths.append(Path(first["audio"]))

            second = process(
                "不存在的音频也能测试，因为 ASR 已被模拟.wav",
                session_id=session_id,
                request_id="test-request-2",
            )
            audio_paths.append(Path(second["audio"]))

        assert len(chat_calls) == 2

        # 第一轮没有历史
        assert chat_calls[0]["history"] == []

        # 两轮都必须使用数据库中的非空人设
        assert chat_calls[0]["persona_content"].strip()
        assert chat_calls[1]["persona_content"].strip()

        # 第二轮必须携带第一轮展开后的 user + assistant 历史
        expected_history = [
            {
                "role": "user",
                "content": "第一轮输入",
            },
            {
                "role": "assistant",
                "content": "第一轮输入的模拟回复",
            },
        ]
        assert chat_calls[1]["history"] == expected_history

        with SessionLocal() as db:
            user = get_default_user(db)
            records = get_recent_conversations(
                db,
                user_id=user.id,
                session_id=session_id,
                limit=10,
            )

            assert [r.user_text for r in records] == [
                "第一轮输入",
                "第二轮输入",
            ]
            assert [r.assistant_text for r in records] == [
                "第一轮输入的模拟回复",
                "第二轮输入的模拟回复",
            ]

        print("[通过] 第一轮没有历史，第二轮正确携带第一轮上下文")
        print("[通过] 两轮均读取数据库人设")
        print("[通过] 两轮对话均已写入 MySQL")

    finally:
        # 清理测试数据库记录
        with SessionLocal() as db:
            records = db.scalars(
                select(ConversationRecord).where(
                    ConversationRecord.session_id == session_id
                )
            ).all()

            for record in records:
                db.delete(record)

            db.commit()

        # 清理模拟音频
        for path in audio_paths:
            path.unlink(missing_ok=True)

        print("[清理] 测试记录和模拟音频已删除")


if __name__ == "__main__":
    main()