"""树成熟信件生成服务"""
from sqlalchemy.orm import Session
from models.models import CheckIn, Letter
from config import LETTER_TEMPLATES


def generate_letter(user_id: int, tree_level: int, db: Session):
    """根据用户情绪历史生成个性化信件"""
    milestones = sorted(LETTER_TEMPLATES.keys())
    eligible = [k for k in milestones if k <= tree_level]
    if not eligible:
        level_key = milestones[0]
    else:
        level_key = max(eligible)
    tmpl = LETTER_TEMPLATES[level_key]

    checkins = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user_id)
        .order_by(CheckIn.create_time.asc())
        .all()
    )

    total = len(checkins)
    emotion_counts = {}
    for c in checkins:
        emotion_counts[c.emotion] = emotion_counts.get(c.emotion, 0) + 1

    top_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "平静"
    top_pct = round(emotion_counts[top_emotion] / total * 100) if total > 0 else 0

    positive = emotion_counts.get("开心", 0) + emotion_counts.get("放松", 0)
    negative = emotion_counts.get("低落", 0) + emotion_counts.get("焦虑", 0) + emotion_counts.get("疲惫", 0)

    if positive > negative:
        mood_desc = "你是一个内心充满阳光的人，积极情绪占了大多数日子"
    elif negative > positive:
        mood_desc = "你经历了不少艰难时刻，但每一次你都走过来了"
    else:
        mood_desc = "你的情绪丰富而真实，每一种感受你都认真对待"

    content = f"{tmpl['intro']}\n\n"
    content += f"📝 这段时间，你一共完成了 {total} 次情绪打卡。{mood_desc}——最常出现的情绪是「{top_emotion}」，它出现了 {top_pct}% 的日子。\n\n"

    for title, emotion_filter, body in tmpl["sections"]:
        if emotion_filter and emotion_filter not in emotion_counts:
            continue
        content += f"【{title}】\n{body}\n\n"

    content += f"【写在最后】\n{tmpl['closing']}"

    emotion_summary = f"总计{total}次打卡, 主要情绪{top_emotion}({top_pct}%), 积极{positive}次 消极{negative}次"

    letter = Letter(
        user_id=user_id,
        tree_level=tree_level,
        title=tmpl["title"],
        content=content,
        emotion_summary=emotion_summary
    )
    db.add(letter)
    db.commit()
    return letter
