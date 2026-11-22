"""test_llm_context.py —— 验证数据库人设与多轮 LLM 消息结构"""
import json
import sys

from database import SessionLocal
from llm import build_messages, chat
from repositories import get_active_persona, get_default_user


def main() -> None:
    with SessionLocal() as db:
        user = get_default_user(db)
        persona = get_active_persona(db, user.id)
        persona_content = persona.content

    # 模拟之前已经发生过的一轮对话
    history = [
        {
            "role": "user",
            "content": "你好，我叫 Liberi。",
        },
        {
            "role": "assistant",
            "content": "你好，Liberi，很高兴认识你。",
        },
    ]

    original_history = history.copy()

    messages = build_messages(
        user_text="请根据前面的对话回答：我叫什么名字？",
        persona_content=persona_content,
        history=history,
    )

    expected_roles = ["system", "user", "assistant", "user"]

    assert [message["role"] for message in messages] == expected_roles
    assert messages[0]["content"] == persona_content
    assert messages[1]["content"] == "你好，我叫 Liberi。"
    assert messages[-1]["role"] == "user"
    assert "我叫什么名字" in messages[-1]["content"]

    # 确认构造函数没有直接修改调用方传入的列表
    assert history == original_history

    print("[消息结构]")
    print(json.dumps(messages, ensure_ascii=False, indent=2))
    print("[通过] 数据库人设与多轮消息结构正确")

    # 加 --live 才会真正请求 DeepSeek，普通测试不消耗 API 调用
    if "--live" in sys.argv:
        print("[DeepSeek] 正在验证模型是否可以使用历史上下文……")

        reply = chat(
            user_text="请根据前面的对话回答：我叫什么名字？",
            persona_content=persona_content,
            history=history,
        )

        print(f"[模型回复] {reply}")
        print("[提示] 回复中应能识别出名字 Liberi")


if __name__ == "__main__":
    main()