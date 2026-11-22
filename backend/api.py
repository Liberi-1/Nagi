"""api.py —— Nagi Web 管理后台 REST API"""
from datetime import datetime
from tts import speak

from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from context_cache import redis_available
from database import SessionLocal, engine
from repositories import (
    get_active_persona,
    get_default_user,
    update_active_persona,
)

from fastapi.responses import JSONResponse, FileResponse

from repositories import (
    get_active_persona,
    get_conversation_page,
    get_default_user,
    update_active_persona,
)

import asyncio
import uuid
from pathlib import Path
from typing import Literal

class UTF8JSONResponse(JSONResponse):
    """显式声明 UTF-8，兼容 Windows PowerShell 等客户端。"""

    media_type = "application/json; charset=utf-8"

app = FastAPI(
    title="Nagi Admin API",
    description="Nagi v0.2 人设与对话管理接口",
    version="0.2.0",
    default_response_class=UTF8JSONResponse,
)

# 仅允许本地 Vue 开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
TTS_TEMP_DIR = Path(__file__).parent / "temp"
TTS_TEMP_DIR.mkdir(exist_ok=True)


class PersonaResponse(BaseModel):
    """返回给前端的当前人设。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    content: str
    is_active: bool
    updated_at: datetime


class PersonaUpdateRequest(BaseModel):
    """网页保存人设时使用的请求体。"""

    name: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=20000)

    @field_validator("name", "content")
    @classmethod
    def strip_and_validate(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("内容不能只包含空白字符")

        return value

class ConversationRecordResponse(BaseModel):
    """返回给前端的一轮对话。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    persona_id: int
    session_id: str
    request_id: str
    user_text: str
    assistant_text: str
    emotion: str
    created_at: datetime


class ConversationPageResponse(BaseModel):
    """对话分页结果。"""

    total: int
    page: int
    page_size: int
    items: list[ConversationRecordResponse]

class TTSPreviewRequest(BaseModel):
    """生成一条临时语音试听。"""

    text: str = Field(min_length=1, max_length=200)
    voice: Literal[
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-XiaoyiNeural",
        "zh-CN-YunxiNeural",
        "zh-CN-YunjianNeural",
    ] = "zh-CN-XiaoxiaoNeural"

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("试听文本不能为空")

        return value

@app.get("/api/health")
def health_check():
    """检查 MySQL；Redis 不可用不会阻断主服务。"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="MySQL 当前不可用",
        )

    return {
        "status": "ok",
        "mysql": "ok",
        "redis": (
            "ok" if redis_available() else "unavailable"
        ),
        "context_fallback": "mysql",
    }


@app.get(
    "/api/personas/active",
    response_model=PersonaResponse,
)
def read_active_persona():
    """读取默认用户当前启用的人设。"""
    try:
        with SessionLocal() as db:
            user = get_default_user(db)
            persona = get_active_persona(db, user.id)
            return persona
    except LookupError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@app.put(
    "/api/personas/active",
    response_model=PersonaResponse,
)
def update_persona(request: PersonaUpdateRequest):
    """修改当前启用人设；下一轮 LLM 请求即可读取新内容。"""
    try:
        with SessionLocal() as db:
            user = get_default_user(db)

            return update_active_persona(
                db,
                user_id=user.id,
                name=request.name,
                content=request.content,
            )
    except LookupError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

@app.get(
    "/api/conversations",
    response_model=ConversationPageResponse,
)
def read_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session_id: str | None = Query(
        default=None,
        max_length=64,
    ),
    emotion: str | None = Query(
        default=None,
        max_length=32,
    ),
):
    """按时间倒序分页查询对话，支持会话和情绪筛选。"""
    try:
        with SessionLocal() as db:
            user = get_default_user(db)

            total, records = get_conversation_page(
                db,
                user_id=user.id,
                page=page,
                page_size=page_size,
                session_id=session_id,
                emotion=emotion,
            )

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": records,
            }

    except LookupError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

@app.post("/api/tts/preview")
async def create_tts_preview(
    request: TTSPreviewRequest,
    background_tasks: BackgroundTasks,
):
    """生成临时 MP3，响应发送完成后自动删除。"""
    output_path = (
        TTS_TEMP_DIR / f"preview-{uuid.uuid4().hex}.mp3"
    )

    try:
        await asyncio.to_thread(
            speak,
            request.text,
            output_path,
            request.voice,
        )

    except Exception as e:
        output_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=502,
            detail=f"TTS 预览生成失败：{e}",
        )

    background_tasks.add_task(
        output_path.unlink,
        missing_ok=True,
    )

    return FileResponse(
        output_path,
        media_type="audio/mpeg",
        filename="nagi-preview.mp3",
    )