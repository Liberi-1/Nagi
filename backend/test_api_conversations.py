"""test_api_conversations.py —— 对话分页、筛选、排序与参数校验测试"""
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


def main() -> None:
    session_id = f"test-api-conversations-{uuid.uuid4().hex}"

    with SessionLocal() as db:
        user = get_default_user(db)
        persona = get_active_persona(db, user.id)
        user_id = user.id
        persona_id = persona.id

        for turn, emotion in enumerate(
            ["neutral", "happy", "neutral"],
            start=1,
        ):
            save_conversation(
                db,
                user_id=user_id,
                persona_id=persona_id,
                session_id=session_id,
                request_id=f"test-api-request-{turn}",
                user_text=f"API 第{turn}轮输入",
                assistant_text=f"API 第{turn}轮回复",
                emotion=emotion,
            )

    try:
        # 第一页：三条记录，每页两条，应返回第三、第二轮
        first_page = api_request(
            "GET",
            f"/api/conversations"
            f"?session_id={session_id}"
            f"&page=1&page_size=2",
        )

        assert first_page["total"] == 3
        assert first_page["page"] == 1
        assert first_page["page_size"] == 2
        assert len(first_page["items"]) == 2

        assert [
            item["user_text"]
            for item in first_page["items"]
        ] == [
            "API 第3轮输入",
            "API 第2轮输入",
        ]

        print("[通过] 第一页总数、条数和倒序排列正确")

        # 第二页应只剩第一轮
        second_page = api_request(
            "GET",
            f"/api/conversations"
            f"?session_id={session_id}"
            f"&page=2&page_size=2",
        )

        assert second_page["total"] == 3
        assert len(second_page["items"]) == 1
        assert (
            second_page["items"][0]["user_text"]
            == "API 第1轮输入"
        )

        print("[通过] 第二页分页边界正确")

        # 会话和情绪组合筛选，只应命中第二轮
        filtered = api_request(
            "GET",
            f"/api/conversations"
            f"?session_id={session_id}"
            f"&emotion=happy"
            f"&page=1&page_size=20",
        )

        assert filtered["total"] == 1
        assert len(filtered["items"]) == 1
        assert filtered["items"][0]["emotion"] == "happy"
        assert (
            filtered["items"][0]["user_text"]
            == "API 第2轮输入"
        )

        print("[通过] session_id 与 emotion 组合筛选正确")

        # 不合法的分页参数应返回 422
        for query in ["page=0", "page_size=0", "page_size=101"]:
            try:
                api_request(
                    "GET",
                    f"/api/conversations?{query}",
                )
                raise AssertionError(
                    f"非法参数未返回 422：{query}"
                )
            except Exception as e:
                # urllib 的 HTTPError 才是预期的参数校验响应
                import urllib.error

                if not isinstance(e, urllib.error.HTTPError):
                    raise
                assert e.code == 422

        print("[通过] 非法分页参数均返回 HTTP 422")

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

        print("[清理] API 测试对话已删除")

    print("[完成] 对话 API 全部测试通过")


if __name__ == "__main__":
    main()