"""test_repositories.py —— 验证人设读取、对话保存与最近 N 轮查询"""
import uuid

from sqlalchemy import select

from database import SessionLocal
from models import ConversationRecord
from repositories import (
    get_active_persona,
    get_default_user,
    get_recent_conversations,
    save_conversation,
)


def main() -> None:
    # 每次测试使用独立会话 ID，不影响真实对话记录
    session_id = f"test-session-{uuid.uuid4().hex}"

    with SessionLocal() as db:
        try:
            user = get_default_user(db)
            persona = get_active_persona(db, user.id)

            assert persona.content.strip(), "启用人设的内容不能为空"
            print(
                f"[人设] {persona.name}"
                f"（内容长度：{len(persona.content)}）"
            )

            for turn in range(1, 4):
                save_conversation(
                    db,
                    user_id=user.id,
                    persona_id=persona.id,
                    session_id=session_id,
                    request_id=f"test-request-{uuid.uuid4().hex}",
                    user_text=f"第{turn}轮",
                    assistant_text=f"第{turn}轮回复",
                )

            print("[保存] 已写入 3 轮测试对话")

            recent = get_recent_conversations(
                db,
                user_id=user.id,
                session_id=session_id,
                limit=2,
            )

            actual = [record.user_text for record in recent]
            expected = ["第2轮", "第3轮"]

            assert actual == expected, (
                f"最近 N 轮查询错误：期望 {expected}，实际 {actual}"
            )

            print(f"[读取] 最近 2 轮：{' -> '.join(actual)}")

        finally:
            # 无论测试成功或失败，都清理本次写入的测试数据
            test_records = db.scalars(
                select(ConversationRecord).where(
                    ConversationRecord.session_id == session_id
                )
            ).all()

            for record in test_records:
                db.delete(record)

            db.commit()
            print("[清理] 本次测试数据已删除")

        remaining = get_recent_conversations(
            db,
            user_id=user.id,
            session_id=session_id,
            limit=10,
        )
        assert remaining == [], "测试数据没有被完全清理"

    print("[通过] Repository 全部验证成功")


if __name__ == "__main__":
    main()