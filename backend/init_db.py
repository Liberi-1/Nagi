"""init_db.py —— 创建数据表，并初始化默认用户与默认人设"""
from pathlib import Path

from sqlalchemy import select

from database import Base, SessionLocal, engine

# 导入模型后，Base.metadata 才能知道需要创建哪些表
from models import ConversationRecord, Persona, User

BASE_DIR = Path(__file__).resolve().parent
PERSONA_PATH = BASE_DIR / "config" / "persona.md"

DEFAULT_USERNAME = "local"
DEFAULT_DISPLAY_NAME = "本地用户"
DEFAULT_PERSONA_NAME = "Nagi"


def init_db() -> None:
    # 只创建尚不存在的表，不会清空已有数据
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.username == DEFAULT_USERNAME)
        )

        if user is None:
            user = User(
                username=DEFAULT_USERNAME,
                display_name=DEFAULT_DISPLAY_NAME,
            )
            db.add(user)
            db.flush()  # 先取得 user.id，供人设外键使用
            print(f"[初始化] 已创建默认用户：{user.username}")

        active_persona = db.scalar(
            select(Persona)
            .where(
                Persona.user_id == user.id,
                Persona.is_active.is_(True),
            )
            .limit(1)
        )

        if active_persona is None:
            content = PERSONA_PATH.read_text(
                encoding="utf-8"
            ).strip()

            active_persona = Persona(
                user_id=user.id,
                name=DEFAULT_PERSONA_NAME,
                content=content,
                is_active=True,
            )
            db.add(active_persona)
            print("[初始化] 已从 persona.md 导入默认人设")
        else:
            print("[检查] 已存在启用人设，不覆盖数据库内容")

        db.commit()

        print("[完成] 数据表初始化成功")
        print(f"默认用户 ID：{user.id}")
        print(f"当前人设 ID：{active_persona.id}")


if __name__ == "__main__":
    init_db()