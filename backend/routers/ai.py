"""AI 暖心寄语 & NLP 情绪分析路由"""
import random
from fastapi import APIRouter, Form
from config import AI_MESSAGES

router = APIRouter()


@router.get("/api/ai/message")
def get_ai_message(emotion: str):
    msgs = AI_MESSAGES.get(emotion)
    if msgs:
        return {"msg": random.choice(msgs)}
    return {"msg": "小树一直陪着你呀～"}


@router.post("/api/ai/analyze-emotion")
def analyze_emotion(text: str = Form(...)):
    from text_features import analyze_emotion as nlp_analyze
    result = nlp_analyze(text)
    return {
        "emotion": result["emotion"],
        "emotion_scores": result["emotion_scores"],
        "intensity": result["intensity"],
        "secondary_emotion": result["secondary_emotion"],
        "sentiment_polarity": result["sentiment_polarity"],
        "text_stats": result["text_stats"],
    }
