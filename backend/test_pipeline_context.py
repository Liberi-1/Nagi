"""test_pipeline_context.py —— 不依赖真实 ASR/LLM/TTS 的多轮上下文测试"""
import uuid
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select

from context_cache import clear_cache, load_cached_history
from database import SessionLocal
from models import ConversationRecord
from pipeline import process
from repositories import get_default_user, get_recent_conversations


chat_calls = []
audio_paths = []

TEST_INPUTS = [
    "第一轮输入",
    "第二轮输入",
    "第三轮输入",
    "第四轮输入",
]


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


def expected_turn_messages(index: int) -> list[dict[str, str]]:
    """生成指定轮次展开后的 user + assistant 消息。"""
    return [
        {
            "role": "user",
            "content": TEST_INPUTS[index],
        },
        {
            "role": "assistant",
            "content": f"{TEST_INPUTS[index]}的模拟回复",
        },
    ]


def main() -> None:
    session_id = f"test-pipeline-{uuid.uuid4().hex}"
    chat_calls.clear()

    try:
        with (
            patch(
                "pipeline.transcribe",
                side_effect=TEST_INPUTS,
            ),
            patch("pipeline.chat", side_effect=fake_chat),
            patch("pipeline.speak", side_effect=fake_speak),
        ):
            for index, user_text in enumerate(TEST_INPUTS, start=1):
                result = process(
                    "不存在的音频也能测试，因为 ASR 已被模拟.wav",
                    session_id=session_id,
                    request_id=f"test-request-{index}",
                )
                audio_paths.append(Path(result["audio"]))

                assert result["text"] == f"{user_text}的模拟回复"
                assert result["session_id"] == session_id

        assert len(chat_calls) == len(TEST_INPUTS)

        # 逐轮构造应当传入 LLM 的完整历史。
        # 第一轮为 0 轮，之后依次为 1、2、3 轮。
        expected_history = []

        for index, call in enumerate(chat_calls, start=1):
            assert call["user_text"] == TEST_INPUTS[index - 1]
            assert call["persona_content"].strip(), (
                f"第 {index} 轮没有读取到数据库人设"
            )

            assert call["history"] == expected_history, (
                f"第 {index} 轮上下文错误。\n"
                f"期望：{expected_history}\n"
                f"实际：{call['history']}"
            )

            expected_history.extend(
                expected_turn_messages(index - 1)
            )

        # 最终 expected_history 应包含四轮、共八条消息。
        assert len(expected_history) == 8

        with SessionLocal() as db:
            user = get_default_user(db)
            user_id = user.id

            records = get_recent_conversations(
                db,
                user_id=user_id,
                session_id=session_id,
                limit=10,
            )

            assert [r.user_text for r in records] == TEST_INPUTS
            assert [r.assistant_text for r in records] == [
                f"{user_text}的模拟回复"
                for user_text in TEST_INPUTS
            ]

        # 直接读取 Redis，防止 Pipeline 通过 MySQL 回退掩盖缓存追加故障。
        cached_history = load_cached_history(
            user_id=user_id,
            session_id=session_id,
            limit=10,
        )

        assert cached_history == expected_history, (
            "Redis 中的四轮缓存与预期不一致。\n"
            f"期望：{expected_history}\n"
            f"实际：{cached_history}"
        )

        print("[通过] 四轮传入 LLM 的历史轮数依次为 0、1、2、3")
        print("[通过] 第三轮和第四轮均携带之前的完整对话")
        print("[通过] 四轮均读取数据库人设")
        print("[通过] 四轮对话均已按顺序写入 MySQL")
        print("[通过] Redis 已累积四轮缓存，而非停留在单一轮")

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

            user = get_default_user(db)
            clear_cache(user.id, session_id)

        # 清理模拟音频
        for path in audio_paths:
            path.unlink(missing_ok=True)

        print("[清理] 测试记录、Redis 缓存和模拟音频已删除")


if __name__ == "__main__":
    main()