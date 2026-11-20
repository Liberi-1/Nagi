"""llm.py —— LLM 模块：人设 + 用户输入 → 回复文本"""
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # 从 .env 读取 DEEPSEEK_API_KEY

PERSONA_PATH = Path(__file__).parent / "config" / "persona.md"

_client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)


def load_persona() -> str:
    """从配置文件读取人设，作为 system prompt。"""
    return PERSONA_PATH.read_text(encoding="utf-8").strip()


def chat(user_text: str) -> str:
    """输入一段用户文本，返回符合人设的回复。"""
    response = _client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": load_persona()},
            {"role": "user", "content": user_text},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()