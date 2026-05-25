"""情绪趋势路由"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import CheckIn
from dependencies import get_current_user
from config import MOOD_SCORE

router = APIRouter()


@router.get("/api/trends/emotion")
def get_emotion_trends(user=Depends(get_current_user), db: Session = Depends(get_db)):
    records = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user.id)
        .order_by(CheckIn.create_time.asc())
        .all()
    )

    trend = []
    dist = {}
    daily_scores = {}

    for r in records:
        date_str = r.create_time.strftime("%Y-%m-%d")
        score = MOOD_SCORE.get(r.emotion, 3)
        trend.append({"date": date_str, "score": score, "emotion": r.emotion})
        dist[r.emotion] = dist.get(r.emotion, 0) + 1
        if date_str not in daily_scores:
            daily_scores[date_str] = []
        daily_scores[date_str].append(score)

    daily_avg = []
    for date_str, scores in sorted(daily_scores.items()):
        daily_avg.append({"date": date_str, "score": round(sum(scores) / len(scores), 2)})

    streak = 0
    today = date.today()
    for i in range(30):
        check_date = today - timedelta(days=i)
        if check_date.strftime("%Y-%m-%d") in daily_scores:
            streak += 1
        else:
            break

    week_ago = date.today() - timedelta(days=7)
    week_records = [r for r in records if r.create_time.date() >= week_ago]
    week_scores = [MOOD_SCORE.get(r.emotion, 3) for r in week_records]
    week_avg = round(sum(week_scores) / len(week_scores), 2) if week_scores else 0

    all_scores = [MOOD_SCORE.get(r.emotion, 3) for r in records]
    total_avg = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0
    top_emotion = max(dist, key=dist.get) if dist else "暂无"

    return {
        "trend": trend,
        "daily_avg": daily_avg,
        "distribution": dist,
        "total_checkins": len(records),
        "total_avg": total_avg,
        "top_emotion": top_emotion,
        "streak": streak,
        "week_avg": week_avg,
        "week_count": len(week_records)
    }
