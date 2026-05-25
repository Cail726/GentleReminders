"""学生认证路由 — 登录/注册/退出"""
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import User
from auth import hash_password, verify_password, needs_rehash
from dependencies import get_current_user, check_login_rate

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    from main import templates
    return templates.TemplateResponse(request, "login.html")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    from main import templates
    return templates.TemplateResponse(request, "register.html")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")


@router.post("/api/register")
def register(
    username: str = Form(...),
    password: str = Form(...),
    nickname: str = Form(""),
    db: Session = Depends(get_db)
):
    username = username.strip()
    if not username or len(username) < 2 or len(username) > 30:
        return {"code": 400, "msg": "用户名需2-30个字符"}
    if not password or len(password) < 6:
        return {"code": 400, "msg": "密码需至少6位"}
    nickname = nickname.strip()[:30] or "小伙伴"
    if db.query(User).filter(User.username == username).first():
        return {"code": 400, "msg": "用户名已存在"}
    new_user = User(username=username, password=hash_password(password), nickname=nickname)
    db.add(new_user)
    db.commit()
    return {"code": 200, "msg": "注册成功"}


@router.post("/api/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    _rate=Depends(check_login_rate),
):
    user = db.query(User).filter(User.username == username.strip()).first()
    if not user or not verify_password(password, user.password):
        return {"code": 400, "msg": "账号或密码错误"}
    if needs_rehash(user.password):
        user.password = hash_password(password)
        db.commit()
    request.session["user_id"] = user.id
    return {"code": 200, "msg": "登录成功", "user_id": user.id}


@router.get("/api/user/info")
def get_user_info(user=Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "nickname": user.nickname}
