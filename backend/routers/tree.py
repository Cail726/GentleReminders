"""心理树 & 信件路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import Tree, Letter
from dependencies import get_current_user

router = APIRouter()


@router.get("/api/tree/info")
def get_tree_info(user=Depends(get_current_user), db: Session = Depends(get_db)):
    tree = db.query(Tree).filter(Tree.user_id == user.id).first()
    if not tree:
        return {"level": 1, "exp": 0, "health": 100}
    return {"level": tree.level, "exp": tree.exp, "health": tree.health}


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
