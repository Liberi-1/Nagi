"""test_api_emotion_stats.py —— 验证情绪聚合计数"""
import uuid

from sqlalchemy import select
from test_api_persona import api_request

from database import SessionLocal
from models import ConversationRecord
from repositories import (
    get_active_persona,
    get_default_user,
    save_conversation,
)

STATS_URL = "/api/conversations/emotion-stats"


def count_of(stats: list[dict], emotion: str) -> int:
    for item in stats:
        if item["emotion"] == emotion:
            return item["count"]
    return 0


def main() -> None:
    baseline = api_request("GET", STATS_URL)
    session_id = f"test-stats-{uuid.uuid4().hex}"

    with SessionLocal() as db:
        user = get_default_user(db)
        persona = get_active_persona(db, user.id)

        for turn, emotion in enumerate(
            ["neutral", "happy", "neutral"],
            start=1,
        ):
            save_conversation(
                db,
                user_id=user.id,
                persona_id=persona.id,
                session_id=session_id,
                request_id=f"test-stats-{turn}",
                user_text=f"统计测试{turn}",
                assistant_text=f"统计回复{turn}",
                emotion=emotion,
            )

    try:
        updated = api_request("GET", STATS_URL)

        neutral_before = count_of(baseline, "neutral")
        happy_before = count_of(baseline, "happy")

        assert count_of(updated, "neutral") == (
            neutral_before + 2
        )
        assert count_of(updated, "happy") == (
            happy_before + 1
        )

        print("[通过] neutral 数量增加 2，happy 数量增加 1")

    finally:
        with SessionLocal() as db:
            records = db.scalars(
                select(ConversationRecord).where(
                    ConversationRecord.session_id == session_id
                )
            ).all()

            for record in records:
                db.delete(record)

            db.commit()

        print("[清理] 统计测试记录已删除")


if __name__ == "__main__":
    main()