"""情绪打卡路由"""
from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import CheckIn, Tree
from dependencies import get_current_user
from config import VALID_EMOTIONS
from utils.letter_service import generate_letter

router = APIRouter()


@router.post("/api/checkin")
def create_checkin(
    emotion: str = Form(...),
    content: str = Form(""),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if emotion not in VALID_EMOTIONS:
        return {"code": 400, "msg": "无效的情绪类型"}
    content = (content or "").strip()[:2000]
    user_id = user.id
    checkin = CheckIn(user_id=user_id, emotion=emotion, content=content)
    db.add(checkin)

    tree = db.query(Tree).filter(Tree.user_id == user_id).first()
    if not tree:
        tree = Tree(user_id=user_id, level=1, exp=0, health=100)
        db.add(tree)

    exp_gain = 10
    if emotion in ["开心", "放松"]:
        exp_gain = 15
        tree.health = min(100, tree.health + 5)
    elif emotion in ["低落", "焦虑", "疲惫"]:
        tree.health = max(0, tree.health - 5)

    old_level = tree.level
    tree.exp += exp_gain
    if tree.exp >= 100:
        tree.exp = 0
        tree.level += 1

    db.commit()

    new_letter = None
    milestone_levels = [5, 10, 15, 20]
    for ml in milestone_levels:
        if old_level < ml and tree.level >= ml:
            new_letter = generate_letter(user_id, tree.level, db)
            break

    result = {
        "status": "ok",
        "tree_level": tree.level,
        "tree_exp": tree.exp,
        "tree_health": tree.health
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
