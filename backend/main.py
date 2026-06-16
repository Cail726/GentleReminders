"""Gentle Reminders — 大学生心理状态辅助评估系统"""
import hashlib
import os
import sys

# Log PORT value immediately so it appears in Railway logs
_port_val = os.environ.get("PORT", "NOT-SET")
sys.stderr.write(f"[GR-DEBUG] PORT={_port_val}\n")
sys.stderr.flush()

from models.database import engine, Base
from starlette.middleware.sessions import SessionMiddleware

Base.metadata.create_all(bind=engine)

# Migration: add must_change_password column to admins + login_attempts table (existing DBs)
from sqlalchemy import text, inspect as sa_inspect
insp = sa_inspect(engine)
if "admins" in insp.get_table_names():
    cols = [c["name"] for c in insp.get_columns("admins")]
    if "must_change_password" not in cols:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE admins ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 1"))
            conn.commit()

# Migration: create login_attempts table for rate limiting
if "login_attempts" not in insp.get_table_names():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE login_attempts (
                ip TEXT NOT NULL,
                attempt_time REAL NOT NULL
            )
        """))
        conn.execute(text("CREATE INDEX idx_login_attempts_ip ON login_attempts(ip)"))
        conn.commit()

# Migration: clean up leftover kaleidoscope experiment (rename fragment_count → tree_level)
with engine.connect() as conn:
    result = conn.execute(text("PRAGMA table_info(letters)"))
    cols = [row[1] for row in result.fetchall()]
    if "fragment_count" in cols and "tree_level" not in cols:
        conn.execute(text("ALTER TABLE letters RENAME COLUMN fragment_count TO tree_level"))
        conn.commit()

# Migration: drop stale kaleidoscopes table from abandoned experiment
if "kaleidoscopes" in insp.get_table_names():
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS kaleidoscopes"))
        conn.commit()


from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "model"))

# 项目根目录（基于当前文件位置，不依赖 CWD）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_raw = os.environ.get("GR_SESSION_SECRET")
SESSION_SECRET = _raw if _raw else hashlib.sha256(os.urandom(32)).hexdigest()[:32]
HTTPS_ONLY = os.environ.get("GR_SESSION_HTTPS", "").lower() in ("1", "true", "yes")

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
    https_only=HTTPS_ONLY,
)

app.mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "frontend"))


# -- CSRF 中间件：为所有 HTML 页面设置 csrf_token Cookie
@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type and "csrf_token" not in request.cookies:
        token = hashlib.sha256(os.urandom(32)).hexdigest()
        response.set_cookie(
            "csrf_token", token,
            max_age=86400, samesite="strict", httponly=False, secure=HTTPS_ONLY
        )
    return response


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


@app.on_event("startup")
def init_admin():
    from models.database import get_db
    from models.models import Admin
    from auth import hash_password

    db = next(get_db())
    if not db.query(Admin).filter(Admin.username == "admin").first():
        default_pw = os.environ.get("GR_ADMIN_PASSWORD")
        if not default_pw:
            print("[GentleReminders] 未设置 GR_ADMIN_PASSWORD，跳过 admin 创建")
        else:
            db.add(Admin(username="admin", password=hash_password(default_pw)))
            db.commit()
            print(f"[GentleReminders] 默认管理员: admin / {default_pw}")
    db.close()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Gentle Reminders 系统启动中... port={port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
