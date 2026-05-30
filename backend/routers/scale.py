"""心理量表路由"""
import json
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import ScaleResponse
from dependencies import get_current_user, json_error, verify_csrf
from config import SCALE_QUESTIONS, SCALE_DIMENSION_ORDER, interpret_dimension, overall_analysis

router = APIRouter()


@router.get("/api/scale/questions")
def get_scale_questions():
    return SCALE_QUESTIONS


@router.post("/api/scale/submit")
def submit_scale(
    answers: str = Form(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    _csrf=Depends(verify_csrf),
):
    answer_dict = {}
    try:
        for pair in answers.split(","):
            qid, score = pair.split(":")
            qid = int(qid)
            score = int(score)
            if qid < 1 or qid > 25 or score < 1 or score > 5:
                return json_error("答案格式无效")
            answer_dict[qid] = score
    except ValueError:
        return json_error("答案格式无效")

    if len(answer_dict) != 25:
        return json_error("请完成全部25道题目")

    dim_scores = {}
    dim_counts = {}
    for q in SCALE_QUESTIONS:
        raw = answer_dict.get(q["id"], 3)
        score = 6 - raw if q["reverse"] else raw
        dim = q["dimension"]
        dim_scores[dim] = dim_scores.get(dim, 0) + score
        dim_counts[dim] = dim_counts.get(dim, 0) + 1

    dim_avg = {}
    total_raw = 0
    for dim in SCALE_DIMENSION_ORDER:
        avg = round(dim_scores[dim] / dim_counts[dim], 2) if dim_counts[dim] > 0 else 0
        dim_avg[dim] = avg
        total_raw += dim_scores[dim]

    total = round(total_raw / len(SCALE_QUESTIONS), 2)

    interpretations = {}
    for dim, avg in dim_avg.items():
        interpretations[dim] = interpret_dimension(avg, dim)

    overall = interpret_dimension(total)

    record = ScaleResponse(
        user_id=user.id,
        scale_type="simplified_wellbeing",
        answers=json.dumps(answer_dict, ensure_ascii=False),
        dimension_scores=json.dumps(dim_avg, ensure_ascii=False),
        total_score=total
    )
    db.add(record)
    db.commit()

    return {
        "id": record.id,
        "total_score": total,
        "dimension_scores": dim_avg,
        "interpretations": interpretations,
        "overall": overall,
        "analysis": overall_analysis(dim_avg, total),
        "time": record.create_time.strftime("%Y-%m-%d %H:%M")
    }


@router.get("/api/scale/history")
def get_scale_history(user=Depends(get_current_user), db: Session = Depends(get_db)):
    records = (
        db.query(ScaleResponse)
        .filter(ScaleResponse.user_id == user.id)
        .order_by(ScaleResponse.create_time.desc())
        .limit(10)
        .all()
    )
    res = []
    for r in records:
        dim_scores = json.loads(r.dimension_scores)
        interpretations = {}
        for dim, avg in dim_scores.items():
            interpretations[dim] = interpret_dimension(avg, dim)
        res.append({
            "id": r.id,
            "scale_type": r.scale_type,
            "total_score": r.total_score,
            "dimension_scores": dim_scores,
            "interpretations": interpretations,
            "overall": interpret_dimension(r.total_score),
            "analysis": overall_analysis(dim_scores, r.total_score),
            "time": r.create_time.strftime("%Y-%m-%d %H:%M")
        })
    return res


@router.get("/api/scale/result/{record_id}")
def get_scale_result(record_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(ScaleResponse).filter(
        ScaleResponse.id == record_id, ScaleResponse.user_id == user.id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
    dim_scores = json.loads(r.dimension_scores)
    interpretations = {}
    for dim, avg in dim_scores.items():
        interpretations[dim] = interpret_dimension(avg, dim)
    return {
        "id": r.id,
        "scale_type": r.scale_type,
        "total_score": r.total_score,
        "dimension_scores": dim_scores,
        "interpretations": interpretations,
        "overall": interpret_dimension(r.total_score),
        "analysis": overall_analysis(dim_scores, r.total_score),
        "time": r.create_time.strftime("%Y-%m-%d %H:%M")
    }
