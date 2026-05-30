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


# -- 里程碑信件 Prompt
LETTER_SYSTEM_PROMPT = """你是住在心灵小树里的一个温柔存在。你是一棵会写信的树。

写信的口吻：
- 像《小王子》一样——简短、诗意、画面感强、温柔
- 像林清玄散文一样——自然意象、人生体悟、不疾不徐
- 像给最好的朋友写信——亲切但不越界，陪伴但不教育
- 用自然意象（风、阳光、叶子、根、泥土、星星、雨、季节）承载情感
- 绝不诊断、不说教、不鸡汤、不打鸡血、不评价用户"做得好"或"需要改进"
- 不出现"建议你……""你应该……""要学会……"
- 你是树，你只是看见了、记住了、陪伴着

你是这棵树的灵魂。你没有评判的能力——你只有记忆和陪伴的能力。你忠实地记录了用户每一天的情绪。你看到ta开心时树叶沙沙响，看到ta低落时树叶安静地垂着。你不催促，不要求，只是在这里。"""

LETTER_USER_PROMPT = """这棵树的第 {milestone} 片叶子刚刚长出来了。这是一个里程碑。

树记录到的真实数据：
- 用户一共打卡了 {total} 次
- 最常见情绪：{top_emotion}（占 {top_pct}%）
- 情绪分布：{emotion_dist}
- 积极情绪（开心+放松）{positive} 次，困难情绪（低落+焦虑+疲惫）{negative} 次
- 连续打卡最长记录：{max_streak} 天

{milestone_context}

根据这些真实数据，请给用户写一封信。格式如下：

第一行：信的标题（6-12个字，诗意但不空洞）
空一行
信的正文（250-400字）：
- 开头：提及这个里程碑的意义，可以和树的状态联系起来
- 中间：自然地提到ta的情绪数据——不是冷冰冰地报数字，而是像在回忆共同经历。比如"这{milestone}天里，有{top_pct}%的日子你的树叶是明亮的"而不是"你的积极情绪占{top_pct}%"
- 结尾：温柔地收束，像风吹过后树叶安静下来。不说"继续加油"，而是像"树会一直在这里"

请只输出标题和正文，不要输出任何标记或格式说明。"""

MILESTONE_CONTEXT = {
    7: '这是第一封信。用户刚刚种下这棵树7天。树还很小，但已经有了最初的样子。这封信要温柔地欢迎ta，让ta感受到这棵树是独一无二的、只属于ta的。',
    21: '21天。用户已经养成了关照自己的习惯。树冠初显。这封信可以提起「情绪粒度」——ta正在学会分辨不同的情绪，这是很重要的能力。',
    50: '50天。这棵树的叶子已经非常茂盛了。ta经历了高光和低谷，树都记得。这封信要传达：这么多天对自己的关照，本身就是一种了不起的力量。',
    100: '100天。一百天的自己。这是非常大的里程碑。这封信要温柔而庄重——不是庆祝「坚持」，而是感恩「陪伴」。树和ta一起走过了100天。',
}


def generate_letter_llm(milestone: int, total: int, top_emotion: str, top_pct: int,
                         emotion_dist: str, positive: int, negative: int,
                         max_streak: int) -> str | None:
    """调用 LLM 生成里程碑信件，失败返回 None。返回格式：第一行标题，空行，正文。"""
    ctx = MILESTONE_CONTEXT.get(milestone, MILESTONE_CONTEXT[7])
    user_prompt = LETTER_USER_PROMPT.format(
        milestone=milestone, total=total, top_emotion=top_emotion,
        top_pct=top_pct, emotion_dist=emotion_dist,
        positive=positive, negative=negative, max_streak=max_streak,
        milestone_context=ctx,
    )
    result = _call_llm(LETTER_SYSTEM_PROMPT, user_prompt, max_tokens=800)
    if result:
        # 提取标题
        lines = result.strip().split("\n")
        if len(lines) >= 3 and lines[0].strip() and not lines[1].strip():
            return result.strip()
    return None
