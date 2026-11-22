"""pipeline.py —— 对话管线：数据库人设、多轮上下文、对话入库"""
import time
import uuid
from pathlib import Path

from asr import transcribe
from database import SessionLocal
from llm import chat
from repositories import (
    get_active_persona,
    get_default_user,
    get_recent_conversations,
    save_conversation,
)
from tts import speak

from context_cache import (
    append_to_cache,
    load_cached_history,
    replace_cache,
)

TEMP_DIR = Path(__file__).parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)

DEFAULT_SESSION_ID = "cli-default"
DEFAULT_CONTEXT_TURNS = 10
# 记录当前进程内发生过 Redis 故障、需要重新校准缓存的会话
_CACHE_FALLBACK_SESSIONS: set[tuple[int, str]] = set()


class StageError(Exception):
    """带阶段信息的管线错误，stage 为 ASR / DB / LLM / TTS。"""

    def __init__(self, stage: str, cause: Exception):
        self.stage = stage
        self.cause = cause
        super().__init__(f"{stage} 阶段失败：{cause}")


def with_retry(func, *args, max_attempts: int = 3, **kwargs):
    """网络操作有限重试：失败后等 1s、2s 再试，最多 3 次。"""
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_attempts:
                raise
            print(
                f"[重试] {func.__name__} 第 {attempt} 次失败"
                f"（{e}），稍后重试"
            )
            time.sleep(attempt)


def load_context(
    session_id: str,
    context_turns: int,
) -> tuple[int, int, str, list[dict[str, str]], str]:
    """
    加载默认用户、启用人设和对话上下文。

    返回：
    user_id、persona_id、人设内容、LLM 历史消息、上下文来源。
    """
    with SessionLocal() as db:
        user = get_default_user(db)
        persona = get_active_persona(db, user.id)

        cache_key = (user.id, session_id)
        history = None
        context_source = ""

        # 发生过缓存故障的会话先跳过 Redis，避免读取旧上下文
        if (
            context_turns > 0
            and cache_key not in _CACHE_FALLBACK_SESSIONS
        ):
            history = load_cached_history(
                user_id=user.id,
                session_id=session_id,
                limit=context_turns,
            )

            if history is not None:
                context_source = "Redis"

        # 缓存未命中、被跳过或不可用：从 MySQL 加载
        if history is None:
            records = []

            if context_turns > 0:
                records = get_recent_conversations(
                    db,
                    user_id=user.id,
                    session_id=session_id,
                    limit=context_turns,
                )

            history = []
            turns = []

            for record in records:
                history.extend([
                    {
                        "role": "user",
                        "content": record.user_text,
                    },
                    {
                        "role": "assistant",
                        "content": record.assistant_text,
                    },
                ])

                turns.append({
                    "user_text": record.user_text,
                    "assistant_text": record.assistant_text,
                })

            if context_turns > 0:
                cache_rebuilt = replace_cache(
                    user_id=user.id,
                    session_id=session_id,
                    turns=turns,
                    max_turns=context_turns,
                )

                if cache_rebuilt:
                    _CACHE_FALLBACK_SESSIONS.discard(cache_key)
                else:
                    _CACHE_FALLBACK_SESSIONS.add(cache_key)

                context_source = "MySQL"
            else:
                context_source = "Disabled"

        return (
            user.id,
            persona.id,
            persona.content,
            history,
            context_source,
        )


def process(
    audio_path: str,
    session_id: str = DEFAULT_SESSION_ID,
    request_id: str | None = None,
    context_turns: int = DEFAULT_CONTEXT_TURNS,
) -> dict:
    """完整跑一轮对话：识别 → 加载上下文 → 回复 → 入库 → 合成。"""
    session_id = session_id.strip()
    request_id = (request_id or uuid.uuid4().hex).strip()

    if not session_id or len(session_id) > 64:
        raise ValueError("session_id 长度必须为 1～64 个字符")
    if not request_id or len(request_id) > 64:
        raise ValueError("request_id 长度必须为 1～64 个字符")
    if context_turns < 0:
        raise ValueError("context_turns 不能小于 0")

    try:
        user_text = transcribe(audio_path)
    except Exception as e:
        raise StageError("ASR", e)

    if not user_text:
        raise StageError(
            "ASR",
            ValueError("没有识别出内容，可能是空录音或噪音"),
        )

    print(f"[ASR] 识别结果：{user_text}")

    try:
        (
            user_id,
            persona_id,
            persona_content,
            history,
            context_source,
        ) = load_context(
            session_id=session_id,
            context_turns=context_turns,
        )

        print(
            f"[上下文] 来源={context_source}，"
            f"历史={len(history) // 2} 轮"
        )
    except Exception as e:
        raise StageError("DB", e)

    try:
        reply_text = with_retry(
            chat,
            user_text,
            persona_content=persona_content,
            history=history,
        )
    except Exception as e:
        raise StageError("LLM", e)

    print(f"[LLM] 回复：{reply_text}")

    try:
        with SessionLocal() as db:
            save_conversation(
                db,
                user_id=user_id,
                persona_id=persona_id,
                session_id=session_id,
                request_id=request_id,
                user_text=user_text,
                assistant_text=reply_text,
                emotion="neutral",
            )
        print("[DB] 本轮对话已保存")
    except Exception as e:
        raise StageError("DB", e)

        if context_turns > 0:
        cache_key = (user_id, session_id)

        cache_saved = append_to_cache(
            user_id=user_id,
            session_id=session_id,
            turn={
                "user_text": user_text,
                "assistant_text": reply_text,
            },
            max_turns=context_turns,
        )

        if cache_saved:
            _CACHE_FALLBACK_SESSIONS.discard(cache_key)
            print("[Redis] 本轮对话已追加到缓存")
        else:
            # 下一次先从 MySQL 重新校准，避免读取故障前的旧缓存
            _CACHE_FALLBACK_SESSIONS.add(cache_key)
            
    # 每轮使用独立音频文件，避免不同请求共同覆盖 reply.mp3
    output_audio = TEMP_DIR / f"{uuid.uuid4().hex}_reply.mp3"

    try:
        audio_out = with_retry(
            speak,
            reply_text,
            output_audio,
        )
    except Exception as e:
        raise StageError("TTS", e)

    print(f"[TTS] 已生成：{audio_out}")

    return {
        "text": reply_text,
        "audio": audio_out,
        "emotion": "neutral",
        "session_id": session_id,
        "request_id": request_id,
    }