"""context_cache.py —— 使用 Redis List 缓存最近 N 轮对话"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from redis import Redis
from redis.exceptions import RedisError

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6379/0",
)
DEFAULT_TTL_SECONDS = int(
    os.getenv("CONTEXT_CACHE_TTL_SECONDS", "604800")
)

Message = dict[str, str]
Turn = dict[str, str]

_client: Redis | None = None


def _get_client() -> Redis:
    """延迟创建 Redis 客户端，避免导入模块时立即连接服务。"""
    global _client

    if _client is None:
        _client = Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

    return _client


def _cache_key(user_id: int, session_id: str) -> str:
    return f"nagi:context:{user_id}:{session_id}"


def _serialize_turn(turn: Turn) -> str:
    return json.dumps(
        {
            "user_text": turn["user_text"],
            "assistant_text": turn["assistant_text"],
        },
        ensure_ascii=False,
    )


def _turn_to_messages(raw_turn: str) -> list[Message]:
    turn = json.loads(raw_turn)

    user_text = str(turn["user_text"]).strip()
    assistant_text = str(turn["assistant_text"]).strip()

    if not user_text or not assistant_text:
        raise ValueError("缓存中存在空对话")

    return [
        {
            "role": "user",
            "content": user_text,
        },
        {
            "role": "assistant",
            "content": assistant_text,
        },
    ]


def redis_available() -> bool:
    """检查 Redis 是否可用，不向外抛出连接异常。"""
    try:
        return bool(_get_client().ping())
    except RedisError:
        return False


def load_cached_history(
    user_id: int,
    session_id: str,
    limit: int,
) -> list[Message] | None:
    """
    读取缓存并转换为 LLM 消息。

    返回 None 表示缓存未命中、缓存损坏或 Redis 不可用；
    调用方随后应从 MySQL 重建上下文。
    """
    if limit <= 0:
        raise ValueError("limit 必须大于 0")

    key = _cache_key(user_id, session_id)

    try:
        # List 按时间正序保存，取末尾 limit 轮就是最近 N 轮
        raw_turns = _get_client().lrange(key, -limit, -1)

        if not raw_turns:
            return None

        history = []
        for raw_turn in raw_turns:
            history.extend(_turn_to_messages(raw_turn))

        return history

    except RedisError as e:
        print(f"[Redis] 读取失败，将回退 MySQL：{e}")
        return None

    except (ValueError, KeyError, TypeError) as e:
        print(f"[Redis] 缓存内容无效，将回退 MySQL：{e}")

        # 损坏的缓存没有保留价值，删除后等待数据库重建
        try:
            _get_client().delete(key)
        except RedisError:
            pass

        return None


def replace_cache(
    user_id: int,
    session_id: str,
    turns: list[Turn],
    max_turns: int,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> bool:
    """用数据库查询结果完整重建某个会话的缓存。"""
    if max_turns <= 0:
        raise ValueError("max_turns 必须大于 0")

    key = _cache_key(user_id, session_id)
    selected_turns = turns[-max_turns:]

    try:
        client = _get_client()
        pipeline = client.pipeline()

        pipeline.delete(key)

        if selected_turns:
            pipeline.rpush(
                key,
                *[
                    _serialize_turn(turn)
                    for turn in selected_turns
                ],
            )
            pipeline.expire(key, ttl_seconds)

        pipeline.execute()
        return True

    except RedisError as e:
        print(f"[Redis] 缓存重建失败，不影响 MySQL 对话：{e}")
        return False


def append_to_cache(
    user_id: int,
    session_id: str,
    turn: Turn,
    max_turns: int,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> bool:
    """追加一轮新对话，只保留最近 max_turns 轮，并续期。"""
    if max_turns <= 0:
        raise ValueError("max_turns 必须大于 0")

    key = _cache_key(user_id, session_id)

    try:
        pipeline = _get_client().pipeline()

        pipeline.rpush(key, _serialize_turn(turn))
        pipeline.ltrim(key, -max_turns, -1)
        pipeline.expire(key, ttl_seconds)
        pipeline.execute()

        return True

    except RedisError as e:
        print(f"[Redis] 新对话缓存失败，不影响 MySQL 对话：{e}")
        return False


def clear_cache(user_id: int, session_id: str) -> bool:
    """删除指定会话缓存，主要用于测试或未来手动重置会话。"""
    try:
        _get_client().delete(_cache_key(user_id, session_id))
        return True
    except RedisError:
        return False