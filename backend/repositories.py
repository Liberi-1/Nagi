"""repositories.py —— 人设与对话记录的数据访问层"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import ConversationRecord, Persona, User

DEFAULT_USERNAME = "local"


def get_default_user(db: Session) -> User:
    """取得 v0.2 使用的默认本地用户。"""
    user = db.scalar(
        select(User).where(User.username == DEFAULT_USERNAME)
    )

    if user is None:
        raise LookupError(
            "默认用户不存在，请先运行 python init_db.py"
        )

    return user


def get_active_persona(db: Session, user_id: int) -> Persona:
    """取得指定用户当前启用的人设。"""
    persona = db.scalar(
        select(Persona)
        .where(
            Persona.user_id == user_id,
            Persona.is_active.is_(True),
        )
        .order_by(Persona.id)
        .limit(1)
    )

    if persona is None:
        raise LookupError(
            f"用户 {user_id} 没有启用人设，请先运行 python init_db.py"
        )

    return persona


def save_conversation(
    db: Session,
    *,
    user_id: int,
    persona_id: int,
    session_id: str,
    request_id: str,
    user_text: str,
    assistant_text: str,
    emotion: str = "neutral",
) -> ConversationRecord:
    """保存一轮完整对话，并返回包含数据库 ID 的记录。"""
    record = ConversationRecord(
        user_id=user_id,
        persona_id=persona_id,
        session_id=session_id,
        request_id=request_id,
        user_text=user_text,
        assistant_text=assistant_text,
        emotion=emotion,
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception:
        db.rollback()
        raise


def get_recent_conversations(
    db: Session,
    *,
    user_id: int,
    session_id: str,
    limit: int = 10,
) -> list[ConversationRecord]:
    """
    读取同一会话最近 limit 轮对话。

    数据库先按 ID 倒序取出最近记录，再反转为时间正序，
    使返回值可以直接按照“较早 → 最新”构造 LLM 上下文。
    """
    if limit <= 0:
        raise ValueError("limit 必须大于 0")

    records = list(
        db.scalars(
            select(ConversationRecord)
            .where(
                ConversationRecord.user_id == user_id,
                ConversationRecord.session_id == session_id,
            )
            .order_by(ConversationRecord.id.desc())
            .limit(limit)
        ).all()
    )

    records.reverse()
    return records