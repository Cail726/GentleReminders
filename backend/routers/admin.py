"""管理后台路由 — 页面 + API"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import Admin, CheckIn
from auth import verify_password, hash_password
from dependencies import get_current_admin, anonymize_user_id, check_login_rate

router = APIRouter()


# -- 页面路由
@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    from main import templates
    return templates.TemplateResponse(request, "admin_login.html")


@router.get("/admin/index", response_class=HTMLResponse)
async def admin_index_page(request: Request, admin=Depends(get_current_admin)):
    from main import templates
    return templates.TemplateResponse(request, "admin_index.html", {"request": request, "active_page": "index"})


@router.get("/admin/checkin-list", response_class=HTMLResponse)
async def admin_checkin_page(request: Request, admin=Depends(get_current_admin)):
    from main import templates
    return templates.TemplateResponse(request, "admin_checkin.html", {"request": request, "active_page": "checkin"})


@router.get("/admin/risk-screen", response_class=HTMLResponse)
async def admin_risk_page(request: Request, admin=Depends(get_current_admin)):
    from main import templates
    return templates.TemplateResponse(request, "admin_risk.html", {"request": request, "active_page": "risk"})


@router.get("/admin/change-password", response_class=HTMLResponse)
async def admin_change_password_page(request: Request):
    if not request.session.get("admin_id"):
        return RedirectResponse(url="/admin/login")
    from main import templates
    return templates.TemplateResponse(request, "admin_change_password.html")


@router.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login")


# -- API
@router.post("/api/admin/login")
def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    _rate=Depends(check_login_rate),
):
    admin = db.query(Admin).filter(Admin.username == username.strip()).first()
    if not admin or not verify_password(password, admin.password):
        return {"code": 400, "msg": "账号密码错误"}
    request.session["admin_id"] = admin.id
    if admin.must_change_password:
        return {"code": 301, "msg": "请先修改默认密码", "redirect": "/admin/change-password"}
    return {"code": 200, "msg": "登录成功"}


@router.post("/api/admin/change-password")
def admin_change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=401, detail="请先登录")
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=401, detail="管理员不存在")
    if not verify_password(old_password, admin.password):
        return {"code": 400, "msg": "原密码错误"}
    if not new_password or len(new_password) < 6:
        return {"code": 400, "msg": "新密码至少6位"}
    admin.password = hash_password(new_password)
    admin.must_change_password = False
    db.commit()
    return {"code": 200, "msg": "密码修改成功，即将跳转"}


@router.get("/api/admin/info")
def get_admin_info(admin=Depends(get_current_admin)):
    return {"username": admin.username}


@router.get("/api/admin/all-checkin")
def get_all_checkin(admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    all_data = db.query(CheckIn).order_by(CheckIn.create_time.desc()).all()
    return [{
        "user_anon": anonymize_user_id(item.user_id),
        "emotion": item.emotion,
        "content": item.content,
        "time": item.create_time.strftime("%Y-%m-%d %H:%M")
    } for item in all_data]


@router.get("/api/admin/risk-user")
def get_risk_user(admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    risk_list = ["低落", "焦虑", "疲惫"]
    data = db.query(CheckIn).filter(CheckIn.emotion.in_(risk_list)).order_by(CheckIn.create_time.desc()).all()
    return [{
        "user_anon": anonymize_user_id(item.user_id),
        "emotion": item.emotion,
        "content": item.content,
        "time": item.create_time.strftime("%Y-%m-%d %H:%M")
    } for item in data]


@router.get("/api/admin/emotion-count")
def emotion_statistics(admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    return {
        "开心": db.query(CheckIn).filter(CheckIn.emotion == "开心").count(),
        "平静": db.query(CheckIn).filter(CheckIn.emotion == "平静").count(),
        "放松": db.query(CheckIn).filter(CheckIn.emotion == "放松").count(),
        "低落": db.query(CheckIn).filter(CheckIn.emotion == "低落").count(),
        "焦虑": db.query(CheckIn).filter(CheckIn.emotion == "焦虑").count(),
        "疲惫": db.query(CheckIn).filter(CheckIn.emotion == "疲惫").count(),
    }
