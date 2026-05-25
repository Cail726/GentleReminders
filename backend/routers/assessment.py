"""MSF-XGBoost 心理评估路由"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import CheckIn, ScaleResponse, Assessment
from dependencies import get_current_user

router = APIRouter()


@router.post("/api/model/assess")
def run_assessment(user=Depends(get_current_user), db: Session = Depends(get_db)):
    from train import predict as model_predict

    checkins = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user.id)
        .order_by(CheckIn.create_time.asc())
        .all()
    )
    scale_records = (
        db.query(ScaleResponse)
        .filter(ScaleResponse.user_id == user.id)
        .order_by(ScaleResponse.create_time.desc())
        .all()
    )

    result = model_predict(checkins, scale_records)

    record = Assessment(
        user_id=user.id,
        dimension_scores=json.dumps(result["dimension_scores"], ensure_ascii=False),
        suggestions=json.dumps(result["suggestions"], ensure_ascii=False),
        feature_summary=json.dumps(result["feature_summary"], ensure_ascii=False),
        confidence=result["data_confidence"]
    )
    db.add(record)
    db.commit()

    result["id"] = record.id
    result["time"] = record.create_time.strftime("%Y-%m-%d %H:%M")
    return result


@router.get("/api/model/history")
def get_assessment_history(user=Depends(get_current_user), db: Session = Depends(get_db)):
    records = (
        db.query(Assessment)
        .filter(Assessment.user_id == user.id)
        .order_by(Assessment.create_time.desc())
        .limit(10)
        .all()
    )
    return [{
        "id": r.id,
        "dimension_scores": json.loads(r.dimension_scores),
        "suggestions": json.loads(r.suggestions),
        "feature_summary": json.loads(r.feature_summary),
        "confidence": r.confidence,
        "time": r.create_time.strftime("%Y-%m-%d %H:%M")
    } for r in records]


@router.get("/api/model/result/{record_id}")
def get_assessment_result(record_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(Assessment).filter(
        Assessment.id == record_id, Assessment.user_id == user.id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {
        "id": r.id,
        "dimension_scores": json.loads(r.dimension_scores),
        "suggestions": json.loads(r.suggestions),
        "feature_summary": json.loads(r.feature_summary),
        "confidence": r.confidence,
        "time": r.create_time.strftime("%Y-%m-%d %H:%M")
    }
