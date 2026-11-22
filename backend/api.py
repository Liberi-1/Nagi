"""api.py —— Nagi Web 管理后台 REST API"""
from datetime import datetime

from fastapi import FastAPI, HTTPException
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

from fastapi.responses import JSONResponse

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