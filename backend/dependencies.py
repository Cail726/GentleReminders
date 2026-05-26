"""FastAPI 依赖注入 — 认证校验 + 工具函数"""
import hashlib
import hmac
import os
import time
from fastapi import Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from models.database import get_db, engine
from models.models import User, Admin


def json_error(msg: str, code: int = 400) -> JSONResponse:
    """返回带正确 HTTP 状态码的错误 JSON"""
    return JSONResponse(status_code=code, content={"code": code, "msg": msg})


def json_ok(**kwargs):
    """返回成功 JSON（HTTP 200），code 默认为 200 但可通过 kwargs 覆盖"""
    data = {"code": 200}
    data.update(kwargs)
    return data

# 登录限流（SQLite 持久化，多 worker 安全）
_RATE_LIMIT_MAX = int(os.environ.get("GR_LOGIN_MAX_ATTEMPTS", "5"))
_RATE_LIMIT_WINDOW = int(os.environ.get("GR_LOGIN_WINDOW_SEC", "900"))


def check_login_rate(request: Request):
    """依赖函数：检查登录频率限制，超限抛出 429"""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - _RATE_LIMIT_WINDOW

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM login_attempts WHERE attempt_time < :cutoff"), {"cutoff": cutoff})
        conn.commit()
        row = conn.execute(
            text("SELECT COUNT(*) FROM login_attempts WHERE ip = :ip"), {"ip": ip}
        ).scalar()

        if row >= _RATE_LIMIT_MAX:
            raise HTTPException(status_code=429, detail="登录尝试过于频繁，请 15 分钟后再试")

        conn.execute(
            text("INSERT INTO login_attempts (ip, attempt_time) VALUES (:ip, :t)"),
            {"ip": ip, "t": now}
        )
        conn.commit()


def anonymize_user_id(user_id: int) -> str:
    h = hashlib.sha256(str(user_id).encode()).hexdigest()[:6]
    return f"用户{h}"


def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return user


def get_current_admin(request: Request, db: Session = Depends(get_db)):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=307, headers={"Location": "/admin/login"})
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=307, headers={"Location": "/admin/login"})
    if admin.must_change_password:
        allowed = ("/admin/change-password", "/api/admin/change-password", "/admin/logout")
        if request.url.path not in allowed:
            raise HTTPException(status_code=307, headers={"Location": "/admin/change-password"})
    return admin


def verify_csrf(request: Request):
    """CSRF 保护：验证 X-CSRF-Token 头与 csrf_token Cookie 一致"""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    cookie_token = request.cookies.get("csrf_token")
    header_token = request.headers.get("X-CSRF-Token")
    if not cookie_token or not header_token:
        raise HTTPException(status_code=403, detail="CSRF 验证失败：缺少 token")
    if not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF 验证失败：token 不匹配")
