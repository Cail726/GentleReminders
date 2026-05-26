"""管理后台路由 — 页面 + 群体统计 API（仅展示汇总数据，不暴露个人信息）"""
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import case, func
from models.database import get_db
from models.models import Admin, CheckIn
from auth import verify_password, hash_password
from dependencies import get_current_admin, check_login_rate, json_error, json_ok, verify_csrf

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


@router.get("/admin/trends", response_class=HTMLResponse)
async def admin_trends_page(request: Request, admin=Depends(get_current_admin)):
    from main import templates
    return templates.TemplateResponse(request, "admin_trends.html", {"request": request, "active_page": "trends"})


@router.get("/admin/risk-overview", response_class=HTMLResponse)
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
    _csrf=Depends(verify_csrf),
):
    admin = db.query(Admin).filter(Admin.username == username.strip()).first()
    if not admin or not verify_password(password, admin.password):
        return json_error("账号密码错误")
    request.session["admin_id"] = admin.id
    if admin.must_change_password:
        return json_ok(code=301, msg="请先修改默认密码", redirect="/admin/change-password")
    return json_ok(msg="登录成功")


@router.post("/api/admin/change-password")
def admin_change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    _rate=Depends(check_login_rate),
    _csrf=Depends(verify_csrf),
):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=401, detail="请先登录")
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=401, detail="管理员不存在")
    if not verify_password(old_password, admin.password):
        return json_error("原密码错误")
    if not new_password or len(new_password) < 6:
        return json_error("新密码至少6位")
    admin.password = hash_password(new_password)
    admin.must_change_password = False
    db.commit()
    return json_ok(msg="密码修改成功，即将跳转")


@router.get("/api/admin/info")
def get_admin_info(admin=Depends(get_current_admin)):
    return {"username": admin.username}


# -- 群体统计 API（仅汇总数据）

@router.get("/api/admin/emotion-count")
def emotion_statistics(admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    """各情绪出现次数（群体汇总）"""
    return {
        "开心": db.query(CheckIn).filter(CheckIn.emotion == "开心").count(),
        "平静": db.query(CheckIn).filter(CheckIn.emotion == "平静").count(),
        "放松": db.query(CheckIn).filter(CheckIn.emotion == "放松").count(),
        "低落": db.query(CheckIn).filter(CheckIn.emotion == "低落").count(),
        "焦虑": db.query(CheckIn).filter(CheckIn.emotion == "焦虑").count(),
        "疲惫": db.query(CheckIn).filter(CheckIn.emotion == "疲惫").count(),
    }


@router.get("/api/admin/daily-trend")
def daily_trend(admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    """最近30天每日打卡数 + 平均情绪（群体汇总）"""
    results = (
        db.query(
            func.date(CheckIn.create_time).label("date"),
            func.count().label("count"),
            func.avg(
                case(
                    (CheckIn.emotion == "开心", 5),
                    (CheckIn.emotion == "放松", 4),
                    (CheckIn.emotion == "平静", 3),
                    (CheckIn.emotion == "低落", 2),
                    (CheckIn.emotion == "焦虑", 1),
                    (CheckIn.emotion == "疲惫", 1),
                    else_=3,
                )
            ).label("avg_mood"),
        )
        .group_by(func.date(CheckIn.create_time))
        .order_by(func.date(CheckIn.create_time).desc())
        .limit(30)
        .all()
    )
    return [
        {"date": str(r.date), "count": r.count, "avg_mood": round(float(r.avg_mood or 0), 2)}
        for r in reversed(results)
    ]


@router.get("/api/admin/risk-distribution")
def risk_distribution(admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    """风险情绪分布：各风险情绪占比 + 每周趋势"""
    risk_emotions = ["低落", "焦虑", "疲惫"]
    total = db.query(CheckIn).count() or 1
    results = {}
    for emo in risk_emotions:
        cnt = db.query(CheckIn).filter(CheckIn.emotion == emo).count()
        results[emo] = {"count": cnt, "pct": round(cnt / total * 100, 1)}

    # 最近4周每周风险占比
    weekly = (
        db.query(
            func.strftime("%Y-%W", CheckIn.create_time).label("week"),
            func.count().label("total_count"),
            func.sum(case((CheckIn.emotion.in_(risk_emotions), 1), else_=0)).label("risk_count"),
        )
        .group_by(func.strftime("%Y-%W", CheckIn.create_time))
        .order_by(func.strftime("%Y-%W", CheckIn.create_time).desc())
        .limit(4)
        .all()
    )
    results["weekly"] = [
        {
            "week": r.week,
            "total": r.total_count,
            "risk": r.risk_count or 0,
            "pct": round((r.risk_count or 0) / max(r.total_count, 1) * 100, 1),
        }
        for r in reversed(weekly)
    ]
    results["total_checkins"] = total
    results["total_users"] = db.query(func.count(func.distinct(CheckIn.user_id))).scalar() or 0

    return results


@router.get("/api/admin/hourly-distribution")
def hourly_distribution(admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    """打卡时段分布（按小时汇总）"""
    results = (
        db.query(
            func.strftime("%H", CheckIn.create_time).label("hour"),
            func.count().label("count"),
        )
        .group_by(func.strftime("%H", CheckIn.create_time))
        .order_by("hour")
        .all()
    )
    buckets = {str(h).zfill(2): 0 for h in range(24)}
    for r in results:
        buckets[r.hour] = r.count
    return buckets
