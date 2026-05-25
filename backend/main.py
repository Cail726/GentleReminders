"""Gentle Reminders — 大学生心理状态辅助评估系统"""
import hashlib
import os
import sys

from models.database import engine, Base
from starlette.middleware.sessions import SessionMiddleware

Base.metadata.create_all(bind=engine)

# Migration: add must_change_password column to admins (existing DBs)
from sqlalchemy import text, inspect as sa_inspect
insp = sa_inspect(engine)
if "admins" in insp.get_table_names():
    cols = [c["name"] for c in insp.get_columns("admins")]
    if "must_change_password" not in cols:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE admins ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 1"))
            conn.commit()

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "model"))

# 项目根目录（基于当前文件位置，不依赖 CWD）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SESSION_SECRET = os.environ.get("GR_SESSION_SECRET", "gr-2026-" + hashlib.sha256(os.urandom(32)).hexdigest()[:16])

app = FastAPI(
    title="Gentle Reminders",
    description="大学生心理状态辅助评估系统",
    version="1.0.0"
)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="gr_session",
    max_age=86400,          # 24 小时
    same_site="lax",
    https_only=False,       # 部署到 HTTPS 后改为 True
)

app.mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "frontend"))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 307 and exc.headers.get("Location"):
        return RedirectResponse(url=exc.headers["Location"], status_code=302)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# -- 注册路由模块
from routers.auth import router as auth_router
from routers.checkin import router as checkin_router
from routers.tree import router as tree_router
from routers.scale import router as scale_router
from routers.assessment import router as assessment_router
from routers.trends import router as trends_router
from routers.ai import router as ai_router
from routers.admin import router as admin_router
from routers.pages import router as pages_router

app.include_router(auth_router)
app.include_router(checkin_router)
app.include_router(tree_router)
app.include_router(scale_router)
app.include_router(assessment_router)
app.include_router(trends_router)
app.include_router(ai_router)
app.include_router(admin_router)
app.include_router(pages_router)


if __name__ == "__main__":
    from models.database import get_db
    from models.models import Admin
    from auth import hash_password

    def init_admin():
        db = next(get_db())
        if not db.query(Admin).filter(Admin.username == "admin").first():
            default_pw = os.environ.get("GR_ADMIN_PASSWORD", "gr2026safe")
            db.add(Admin(username="admin", password=hash_password(default_pw)))
            db.commit()
            print(f"[GentleReminders] 默认管理员: admin / {default_pw}")
        db.close()

    init_admin()

    import uvicorn
    print("Gentle Reminders 系统启动中...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
