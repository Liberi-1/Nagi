"""models.py —— Nagi v0.2 数据库模型"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class User(Base):
    """本地用户。v0.2 先使用一个默认用户，不引入登录系统。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )


class Persona(Base):
    """角色人设，content 保存完整的 system prompt。"""

    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ConversationRecord(Base):
    """一轮完整对话：一条用户输入及其对应的角色回复。"""

    __tablename__ = "conversation_records"

    __table_args__ = (
        Index(
            "ix_conversation_records_session_id_id",
            "session_id",
            "id",
        ),
        Index(
            "ix_conversation_records_created_at_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    persona_id: Mapped[int] = mapped_column(
        ForeignKey("personas.id"),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    user_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    assistant_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    emotion: Mapped[str] = mapped_column(
        String(32),
        default="neutral",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )