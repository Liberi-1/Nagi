"""test_context_cache.py —— Redis 命中、重建、裁剪与故障测试"""
import uuid
from unittest.mock import patch

from redis import Redis

import context_cache as cache


def main() -> None:
    user_id = 999001
    session_id = f"test-cache-{uuid.uuid4().hex}"

    turns = [
        {
            "user_text": f"第{i}轮输入",
            "assistant_text": f"第{i}轮回复",
        }
        for i in range(1, 4)
    ]

    try:
        assert cache.redis_available(), "Redis 当前不可用"
        assert cache.clear_cache(user_id, session_id)

        # 初始状态应为缓存未命中
        assert cache.load_cached_history(
            user_id,
            session_id,
            limit=2,
        ) is None

        # 模拟用三轮 MySQL 记录重建缓存，但最多保留两轮
        assert cache.replace_cache(
            user_id,
            session_id,
            turns=turns,
            max_turns=2,
        )

        history = cache.load_cached_history(
            user_id,
            session_id,
            limit=2,
        )

        assert history is not None
        assert [message["content"] for message in history] == [
            "第2轮输入",
            "第2轮回复",
            "第3轮输入",
            "第3轮回复",
        ]

        print("[通过] 缓存重建、命中和时间顺序正确")

        # 追加第四轮后，应只保留第三、第四轮
        assert cache.append_to_cache(
            user_id,
            session_id,
            turn={
                "user_text": "第4轮输入",
                "assistant_text": "第4轮回复",
            },
            max_turns=2,
        )

        history = cache.load_cached_history(
            user_id,
            session_id,
            limit=2,
        )

        assert history is not None
        assert [message["content"] for message in history] == [
            "第3轮输入",
            "第3轮回复",
            "第4轮输入",
            "第4轮回复",
        ]

        print("[通过] 新对话追加与最近 N 轮裁剪正确")

        # 模拟 Redis 连接到未开放端口：所有操作都应安全降级
        unavailable_client = Redis(
            host="127.0.0.1",
            port=6399,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
        )

        with patch.object(cache, "_client", unavailable_client):
            assert cache.load_cached_history(
                user_id,
                session_id,
                limit=2,
            ) is None

            assert cache.append_to_cache(
                user_id,
                session_id,
                turn=turns[0],
                max_turns=2,
            ) is False

        print("[通过] Redis 不可用时不会抛出异常或破坏主流程")

    finally:
        cache.clear_cache(user_id, session_id)
        print("[清理] 测试缓存已删除")


if __name__ == "__main__":
    main()