"""心理树 & 信件路由"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import Tree, Letter, CheckIn
from dependencies import get_current_user
from config import get_tree_stage

router = APIRouter()


@router.get("/api/tree/info")
def get_tree_info(user=Depends(get_current_user), db: Session = Depends(get_db)):
    tree = db.query(Tree).filter(Tree.user_id == user.id).first()
    if not tree:
        return {
            "level": 1, "exp": 0, "health": 100,
            "stage": 1, "stage_name": "种子", "stage_emoji": "🌰",
            "stage_desc": "一颗种子在泥土中沉睡，等待第一缕阳光",
        }

    last_checkin = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user.id)
        .order_by(CheckIn.create_time.desc())
        .first()
    )
    health = tree.health
    if last_checkin:
        days_since = (date.today() - last_checkin.create_time.date()).days
        if days_since > 3:
            decay = (days_since - 3) * 2
            health = max(60, tree.health - decay)

    stage = get_tree_stage(tree.level)
    return {
        "level": tree.level,
        "exp": tree.exp,
        "health": health,
        "stage": stage["stage"],
        "stage_name": stage["name"],
        "stage_emoji": stage["emoji"],
        "stage_desc": stage["desc"],
    }


@router.get("/api/letters")
def get_letters(user=Depends(get_current_user), db: Session = Depends(get_db)):
    letters = (
        db.query(Letter)
        .filter(Letter.user_id == user.id)
        .order_by(Letter.create_time.desc())
        .all()
    )
    return [{
        "id": letter.id,
        "title": letter.title,
        "tree_level": letter.tree_level,
        "emotion_summary": letter.emotion_summary,
        "time": letter.create_time.strftime("%Y-%m-%d %H:%M")
    } for letter in letters]


@router.get("/api/letter/{letter_id}")
def get_letter(letter_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    letter = db.query(Letter).filter(Letter.id == letter_id, Letter.user_id == user.id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件不存在")
    return {
        "id": letter.id,
        "title": letter.title,
        "content": letter.content,
        "tree_level": letter.tree_level,
        "emotion_summary": letter.emotion_summary,
        "time": letter.create_time.strftime("%Y-%m-%d %H:%M")
    }
