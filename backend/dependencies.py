"""FastAPI 依赖注入 — 认证校验 + 工具函数"""
import hashlib
import os
import time
from collections import defaultdict
from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import User, Admin

# 登录限流：每个 IP 窗口内最多尝试次数
_RATE_LIMIT_MAX = int(os.environ.get("GR_LOGIN_MAX_ATTEMPTS", "5"))
_RATE_LIMIT_WINDOW = int(os.environ.get("GR_LOGIN_WINDOW_SEC", "900"))
_login_attempts = defaultdict(list)


def _cleanup_old_attempts(ip: str):
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _RATE_LIMIT_WINDOW]


def check_login_rate(request: Request):
    """依赖函数：检查登录频率限制，超限抛出 429"""
    ip = request.client.host if request.client else "unknown"
    _cleanup_old_attempts(ip)
    if len(_login_attempts[ip]) >= _RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="登录尝试过于频繁，请 15 分钟后再试")
    _login_attempts[ip].append(time.time())


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
