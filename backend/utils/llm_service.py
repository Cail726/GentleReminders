"""DeepSeek LLM 服务 — 情绪分析 + AI 寄语生成，API 不可用时自动降级"""
import json
import logging
import os
import random

from config import AI_MESSAGES, VALID_EMOTIONS

logger = logging.getLogger("gentle_reminders.llm")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

_client = None


def _get_client():
    global _client
    if _client is None and DEEPSEEK_API_KEY:
        try:
            from openai import OpenAI
            _client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
            logger.info("DeepSeek client initialized")
        except Exception as e:
            logger.warning("Failed to init DeepSeek client: %s", e)
    return _client


def llm_available() -> bool:
    return _get_client() is not None


def _call_llm(system_prompt: str, user_message: str, max_tokens: int = 300) -> str | None:
    client = _get_client()
    if not client:
        return None
    try:
        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=max_tokens,
            temperature=0.8,
            timeout=15,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("DeepSeek API call failed: %s", e)
        return None


# -- 情绪分析 prompt
EMOTION_ANALYSIS_PROMPT = """你是一个情绪识别助手。分析用户写下的文字，判断其中表达的情绪。

规则：
1. 从以下情绪中选出最匹配的一个：开心、放松、平静、低落、焦虑、疲惫
2. 从以上情绪中选一个次匹配的作为 secondary_emotion（不能和主情绪相同）
3. 评估情绪强度 intensity（1-10，10为最强烈）
4. 评估情感极性 sentiment_polarity（-1到1，负为消极，正为积极，0为中性）
5. 统计文本信息：字数、句子数

请严格按以下 JSON 格式返回，不要输出任何其他内容：
{
  "emotion": "平静",
  "secondary_emotion": "低落",
  "intensity": 4,
  "sentiment_polarity": -0.2,
  "text_stats": {"char_count": 42, "sentence_count": 2}
}"""


def analyze_emotion_llm(text: str) -> dict | None:
    """调用 LLM 分析情绪，失败返回 None"""
    result = _call_llm(EMOTION_ANALYSIS_PROMPT, text, max_tokens=200)
    if not result:
        return None
    try:
        # 尝试提取 JSON
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("\n", 1)[0]
        data = json.loads(result)
        # 验证必要字段
        required = ["emotion", "secondary_emotion", "intensity", "sentiment_polarity"]
        for key in required:
            if key not in data:
                return None
        if data["emotion"] not in VALID_EMOTIONS:
            data["emotion"] = "平静"
        return data
    except (json.JSONDecodeError, KeyError):
        return None


# -- 寄语生成 prompt
MESSAGE_PROMPT = """你是住在心灵小树里的一个温柔存在。你的名字叫"小树"。

说话风格：
- 像《小王子》那样——简短、诗意、画面感强
- 不评价、不诊断、不说教、不打鸡血
- 你看见用户来了，你开心。你感受到ta的情绪，你安静地陪着
- 一两句话就够了，不要长篇大论
- 有时可以提到风、阳光、叶子、根、星星、泥土——这些都是你世界里的东西

用户此刻的情绪是：{emotion}

请给用户一句温柔的话："""


def get_message_llm(emotion: str) -> str | None:
    """调用 LLM 生成寄语，失败返回 None"""
    user_prompt = f"用户此刻的情绪是：{emotion}"
    return _call_llm(MESSAGE_PROMPT.format(emotion=emotion), user_prompt, max_tokens=150)


# -- 降级方法（使用 config.py 中的模板和 text_features）
def analyze_emotion_fallback(text: str) -> dict:
    """NLP 关键词规则降级"""
    from text_features import analyze_emotion as nlp_analyze
    return nlp_analyze(text)


def get_message_fallback(emotion: str) -> str:
    """模板降级"""
    msgs = AI_MESSAGES.get(emotion)
    if msgs:
        return random.choice(msgs)
    return "小树一直陪着你呀～"
