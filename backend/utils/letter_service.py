"""树成熟信件生成服务 — LLM 优先生成，模板降级"""
from sqlalchemy.orm import Session
from models.models import CheckIn, Letter
from config import LETTER_TEMPLATES


def generate_letter(user_id: int, tree_level: int, db: Session):
    """根据用户情绪历史生成个性化信件。先尝试 DeepSeek LLM，失败则使用模板。"""
    checkins = (
        db.query(CheckIn)
        .filter(CheckIn.user_id == user_id)
        .order_by(CheckIn.create_time.asc())
        .all()
    )

    total = len(checkins)

    # 情绪统计
    emotion_counts = {}
    for c in checkins:
        emotion_counts[c.emotion] = emotion_counts.get(c.emotion, 0) + 1

    top_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "平静"
    top_pct = round(emotion_counts[top_emotion] / total * 100) if total > 0 else 0
    positive = emotion_counts.get("开心", 0) + emotion_counts.get("放松", 0)
    negative = emotion_counts.get("低落", 0) + emotion_counts.get("焦虑", 0) + emotion_counts.get("疲惫", 0)

    # 情绪分布描述
    dist_items = [f"{k}{v}次" for k, v in sorted(emotion_counts.items(), key=lambda x: -x[1])]
    emotion_dist = "、".join(dist_items)

    # 最长连续打卡
    from datetime import timedelta
    dates = sorted(set(c.create_time.date() for c in checkins))
    max_streak = 1
    current = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 1

    # -- 尝试 LLM 生成
    llm_title = None
    llm_content = None
    try:
        from utils.llm_service import generate_letter_llm
        result = generate_letter_llm(
            milestone=tree_level, total=total, top_emotion=top_emotion,
            top_pct=top_pct, emotion_dist=emotion_dist,
            positive=positive, negative=negative, max_streak=max_streak,
        )
        if result:
            lines = result.strip().split("\n")
            # 格式：第一行标题，第二行空行，后续正文
            if len(lines) >= 3 and lines[0].strip() and not lines[1].strip():
                llm_title = lines[0].strip()
                llm_content = "\n".join(lines[2:]).strip()
    except Exception:
        pass

    # -- LLM 失败则使用模板
    if llm_title and llm_content:
        title = llm_title
        content = llm_content
        source = "llm"
    else:
        milestones = sorted(LETTER_TEMPLATES.keys())
        eligible = [k for k in milestones if k <= tree_level]
        level_key = max(eligible) if eligible else milestones[0]
        tmpl = LETTER_TEMPLATES[level_key]

        if positive > negative:
            mood_desc = "你是一个内心充满阳光的人，积极情绪占了大多数日子"
        elif negative > positive:
            mood_desc = "你经历了不少艰难时刻，但每一次你都走过来了"
        else:
            mood_desc = "你的情绪丰富而真实，每一种感受你都认真对待"

        content = f"{tmpl['intro']}\n\n"
        content += f"📝 这段时间，你一共完成了 {total} 次情绪打卡。{mood_desc}——最常出现的情绪是「{top_emotion}」，它出现在了 {top_pct}% 的日子里。\n\n"

        for section_title, emotion_filter, body in tmpl["sections"]:
            if emotion_filter and emotion_filter not in emotion_counts:
                continue
            content += f"【{section_title}】\n{body}\n\n"

        content += f"【写在最后】\n{tmpl['closing']}"
        title = tmpl["title"]
        source = "template"

    emotion_summary = f"总计{total}次打卡, 主要情绪{top_emotion}({top_pct}%), 积极{positive}次 消极{negative}次"

    letter = Letter(
        user_id=user_id,
        tree_level=tree_level,
        title=title,
        content=content,
        emotion_summary=emotion_summary
    )
    db.add(letter)
    db.commit()
    return letter
