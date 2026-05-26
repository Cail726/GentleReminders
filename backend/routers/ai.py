"""AI 暖心寄语 & 情绪分析路由 — DeepSeek LLM + 模板降级"""
from fastapi import APIRouter, Depends, Form
from dependencies import verify_csrf

router = APIRouter()


@router.get("/api/ai/message")
def get_ai_message(emotion: str):
    from utils.llm_service import get_message_llm, get_message_fallback

    llm_msg = get_message_llm(emotion)
    if llm_msg:
        return {"msg": llm_msg, "source": "llm"}
    return {"msg": get_message_fallback(emotion), "source": "fallback"}


@router.post("/api/ai/analyze-emotion")
def analyze_emotion(text: str = Form(...), _csrf=Depends(verify_csrf)):
    from utils.llm_service import analyze_emotion_llm, analyze_emotion_fallback

    result = analyze_emotion_llm(text)
    source = "llm"
    if not result:
        result = analyze_emotion_fallback(text)
        source = "fallback"

    return {
        "emotion": result["emotion"],
        "source": source,
        "emotion_scores": result.get("emotion_scores", {}),
        "intensity": result.get("intensity", 5),
        "secondary_emotion": result.get("secondary_emotion", ""),
        "sentiment_polarity": result.get("sentiment_polarity", 0),
        "text_stats": result.get("text_stats", {}),
    }
