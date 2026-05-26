"""情绪打卡路由"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import CheckIn, Tree
from dependencies import get_current_user, json_error, verify_csrf
from config import VALID_EMOTIONS, get_tree_stage, pick_whisper
from utils.letter_service import generate_letter

router = APIRouter()


@router.post("/api/checkin")
def create_checkin(
    emotion: str = Form(...),
    content: str = Form(""),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _csrf=Depends(verify_csrf),
):
    if emotion not in VALID_EMOTIONS:
        return json_error("无效的情绪类型")
    content = (content or "").strip()[:2000]
    user_id = user.id

    checkin = CheckIn(user_id=user_id, emotion=emotion, content=content)
    db.add(checkin)
    db.commit()

    tree = db.query(Tree).filter(Tree.user_id == user_id).first()
    is_first_tree = tree is None
    if not tree:
        tree = Tree(user_id=user_id, level=1, exp=0, health=100)
        db.add(tree)

    old_level = tree.level

    # 固定成长：无论什么情绪，每次签到 +15 经验
    tree.exp += 15
    is_level_up = False
    if tree.exp >= 100:
        tree.exp -= 100
        tree.level += 1
        is_level_up = True

    # 健康值：每次签到 +5（上限 100），不受情绪影响
    tree.health = min(100, tree.health + 5)

    db.commit()

    # 计算连续签到天数 & 间隔天数（用于树语）
    all_checkins = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user_id)
        .order_by(CheckIn.create_time.desc())
        .all()
    )

    streak = 0
    today = date.today()
    for i in range(30):
        check_date = today - timedelta(days=i)
        if any(c.create_time.date() == check_date for c in all_checkins):
            streak += 1
        else:
            break

    gap_days = 0
    if len(all_checkins) >= 2:
        prev_date = all_checkins[1].create_time.date()
        gap_days = (today - prev_date).days

    whisper = pick_whisper(streak, is_first_tree, is_level_up, gap_days)

    # 里程碑信件（5, 10, 15, 20）
    new_letter = None
    milestone_levels = [5, 10, 15, 20]
    for ml in milestone_levels:
        if old_level < ml <= tree.level:
            new_letter = generate_letter(user_id, tree.level, db)
            break

    stage = get_tree_stage(tree.level)

    result = {
        "status": "ok",
        "tree_level": tree.level,
        "tree_exp": tree.exp,
        "tree_health": tree.health,
        "stage": stage["stage"],
        "stage_name": stage["name"],
        "stage_emoji": stage["emoji"],
        "stage_desc": stage["desc"],
        "streak": streak,
        "whisper": whisper,
    }
    if new_letter:
        result["new_letter"] = {"id": new_letter.id, "title": new_letter.title}
    return result


@router.get("/api/checkin/list")
def get_checkin_list(user=Depends(get_current_user), db: Session = Depends(get_db)):
    records = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user.id)
        .order_by(CheckIn.create_time.desc())
        .all()
    )
    return [{
        "emotion": item.emotion,
        "content": item.content,
        "time": item.create_time.strftime("%Y-%m-%d %H:%M")
    } for item in records]
