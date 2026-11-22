"""llm.py —— LLM 模块：人设 + 历史消息 + 用户输入 → 回复文本"""
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # 从 .env 读取 DEEPSEEK_API_KEY

PERSONA_PATH = Path(__file__).parent / "config" / "persona.md"

Message = dict[str, str]

_client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)


def load_persona() -> str:
    """
    从配置文件读取人设。

    用于兼容旧测试和独立调用；v0.2 主 Pipeline 将传入数据库人设。
    """
    return PERSONA_PATH.read_text(encoding="utf-8").strip()


def build_messages(
    user_text: str,
    persona_content: str,
    history: list[Message] | None = None,
) -> list[Message]:
    """构造发送给 LLM 的完整消息列表，不修改传入的 history。"""
    user_text = user_text.strip()
    persona_content = persona_content.strip()

    if not user_text:
        raise ValueError("用户输入不能为空")
    if not persona_content:
        raise ValueError("人设内容不能为空")

    messages: list[Message] = [
        {
            "role": "system",
            "content": persona_content,
        }
    ]

    for message in history or []:
        role = message.get("role", "")
        content = message.get("content", "").strip()

        # 历史消息只允许用户和角色，不允许通过历史注入新的 system
        if role not in {"user", "assistant"}:
            raise ValueError(f"不支持的历史消息角色：{role}")
        if not content:
            raise ValueError("历史消息内容不能为空")

        messages.append({
            "role": role,
            "content": content,
        })

    messages.append({
        "role": "user",
        "content": user_text,
    })

    return messages


def chat(
    user_text: str,
    persona_content: str | None = None,
    history: list[Message] | None = None,
) -> str:
    """
    输入用户文本，返回符合人设的回复。

    persona_content 为 None 时兼容 v0.1，读取 persona.md；
    传入数据库人设和历史消息后，启用 v0.2 多轮对话。
    """
    if persona_content is None:
        persona_content = load_persona()

    messages = build_messages(
        user_text=user_text,
        persona_content=persona_content,
        history=history,
    )

    response = _client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()