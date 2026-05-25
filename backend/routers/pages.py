"""学生页面路由"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from dependencies import get_current_user

router = APIRouter()


def _page(request: Request, template: str, active_page: str):
    from main import templates
    return templates.TemplateResponse(request, template, {"request": request, "active_page": active_page})


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, user=Depends(get_current_user)):
    return _page(request, "index.html", "index")


@router.get("/checkin", response_class=HTMLResponse)
async def checkin(request: Request, user=Depends(get_current_user)):
    return _page(request, "checkin.html", "checkin")


@router.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, user=Depends(get_current_user)):
    return _page(request, "profile.html", "profile")


@router.get("/scale", response_class=HTMLResponse)
async def scale_page(request: Request, user=Depends(get_current_user)):
    return _page(request, "scale.html", "scale")


@router.get("/trends", response_class=HTMLResponse)
async def trends_page(request: Request, user=Depends(get_current_user)):
    return _page(request, "trends.html", "trends")


@router.get("/assessment", response_class=HTMLResponse)
async def assessment_page(request: Request, user=Depends(get_current_user)):
    return _page(request, "assessment.html", "assessment")


@router.get("/letters", response_class=HTMLResponse)
async def letters_page(request: Request, user=Depends(get_current_user)):
    return _page(request, "letters.html", "letters")
