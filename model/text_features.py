"""文本情绪特征提取 — 加权词典 + 程度修饰 + 否定处理 + 多情绪分布

纯 Python 实现，无需额外 NLP 库。可作为独立模块使用，也可为 MSF-XGBoost 提供特征。
"""

import re

# ===================== 加权情绪词典 =====================
EMOTION_LEXICON = {
    "开心": {
        3: ["太棒了", "超级开心", "幸福极了", "欣喜若狂", "心花怒放", "欢天喜地", "乐开了花", "爽翻了"],
        2: ["开心", "快乐", "高兴", "幸福", "喜悦", "兴奋", "愉快", "欢乐", "满足", "充实",
            "美滋滋", "乐呵呵", "喜洋洋", "好开心", "很开心", "真开心", "超爽", "真爽"],
        1: ["不错", "挺好", "还好吧", "还行吧", "可以", "满意", "舒服", "欣慰", "庆幸",
            "微笑", "嘻嘻", "哈哈", "呵呵", "嘿嘿", "nice", "棒", "赞", "不错哦"],
    },
    "放松": {
        3: ["无比放松", "彻底放松", "舒适极了", "惬意无比", "悠然自得", "心旷神怡"],
        2: ["放松", "舒服", "舒适", "安逸", "惬意", "轻松", "自在", "舒畅", "舒心",
            "好舒服", "真舒服", "很放松", "好轻松"],
        1: ["还好", "还行", "一般般", "凑合", "平静", "安稳", "踏实", "淡定", "从容"],
    },
    "平静": {
        3: ["心如止水", "波澜不惊", "异常平静", "出奇平静"],
        2: ["平静", "安静", "宁静", "冷静", "平和", "淡然", "沉稳", "镇定", "没什么特别"],
        1: ["日常", "普通", "正常", "照常", "一如既往", "按部就班", "还行", "还好"],
    },
    "低落": {
        3: ["崩溃", "绝望", "痛苦至极", "生无可恋", "心如刀绞", "痛不欲生", "万念俱灰"],
        2: ["难过", "伤心", "低落", "沮丧", "悲伤", "忧郁", "消沉", "失落", "心碎",
            "不开心", "不高兴", "好难过", "真难过", "很伤心", "好伤心", "想哭", "委屈"],
        1: ["不开心", "不太高兴", "有点郁闷", "没精神", "没劲", "无聊", "没意思",
            "闷闷不乐", "提不起劲", "没什么兴趣", "不开心吧", "不太舒服",
            "心情不好", "情绪不好"],
    },
    "焦虑": {
        3: ["极度焦虑", "恐慌发作", "惊恐万分", "惶惶不安", "坐立不安", "寝食难安"],
        2: ["焦虑", "担心", "紧张", "害怕", "恐惧", "不安", "烦躁", "慌张", "忧虑",
            "压力", "压力大", "压力好大", "好焦虑", "很紧张", "真担心", "好害怕",
            "心慌", "慌慌张张", "忐忑"],
        1: ["有点担心", "有点紧张", "不太安心", "有点慌", "心神不宁", "隐隐不安",
            "不太踏实", "有点烦", "怪怪的", "七上八下", "不安心", "睡不着", "失眠"],
    },
    "疲惫": {
        3: ["精疲力竭", "累趴了", "透支了", "快要累死", "筋疲力尽", "身心俱疲", "疲惫不堪"],
        2: ["疲惫", "好累", "真累", "很累", "太累了", "困倦", "累死", "累坏", "疲倦",
            "乏力", "没力气", "浑身无力", "累得", "累到", "不想动", "动不了"],
        1: ["有点累", "稍微累", "犯困", "想睡觉", "不太想动", "没睡好", "没精神",
            "提不起神", "昏昏沉沉", "打哈欠", "困了"],
    },
}

# 情绪反转映射（否定时使用）
EMOTION_NEGATION_MAP = {
    "开心": "低落", "放松": "焦虑", "平静": "焦虑",
    "低落": "开心", "焦虑": "放松", "疲惫": "放松",
}

# ===================== 程度修饰词 =====================
INTENSIFIERS = {
    "超级": 2.5, "极其": 2.5, "无比": 2.5, "极度": 2.5,
    "非常": 2.0, "特别": 2.0, "十分": 1.8, "格外": 1.8, "分外": 1.8,
    "很": 1.5, "好": 1.3, "真": 1.5, "真的": 1.5, "太": 1.8,
    "多么": 1.8, "这么": 1.5, "那么": 1.5, "相当": 1.5,
}

DIMINISHERS = {
    "有点": 0.5, "稍微": 0.5, "略微": 0.5, "略": 0.6,
    "还算": 0.7, "不太": 0.5, "不怎么": 0.4, "没啥": 0.4,
    "一点点": 0.4, "一丁点": 0.3, "勉强": 0.6, "凑合": 0.6,
    "差不多": 0.7, "基本上": 0.7, "大体上": 0.7,
}

NEGATION_WORDS = {"不", "没", "没有", "不是", "并非", "无", "毫无", "并非真的"}


def _find_emotion_words(text):
    """扫描文本，返回 [(位置, 情绪类别, 权重, 匹配词)] 列表"""
    hits = []
    for emotion, weight_dict in EMOTION_LEXICON.items():
        for weight, words in weight_dict.items():
            for word in words:
                idx = text.find(word)
                if idx != -1:
                    hits.append((idx, emotion, weight, word))
    hits.sort()
    return hits


def _check_modifier(text, pos):
    """检查位置 pos 前是否有程度修饰词或否定词"""
    before = text[:pos]
    # 取前5个字符检查
    check_window = before[-5:] if len(before) >= 5 else before

    modifier = None
    modifier_mult = 1.0
    negated = False

    # 先检查否定词
    for neg in sorted(NEGATION_WORDS, key=len, reverse=True):
        if check_window.endswith(neg):
            negated = True
            break

    # 再检查程度修饰词
    if not negated:
        for mod, mult in sorted(INTENSIFIERS.items(), key=lambda x: -len(x[0])):
            if check_window.endswith(mod):
                modifier = mod
                modifier_mult = mult
                break
        if modifier is None:
            for mod, mult in sorted(DIMINISHERS.items(), key=lambda x: -len(x[0])):
                if check_window.endswith(mod):
                    modifier = mod
                    modifier_mult = mult
                    break

    return negated, modifier_mult


def extract_text_features(text):
    """从单条文本中提取15+维特征

    Args:
        text: 日记文本字符串

    Returns:
        dict of feature_name -> value
    """
    if not text or not text.strip():
        return {
            "char_count": 0, "sentence_count": 0, "avg_sentence_length": 0.0,
            "emotion_scores": {}, "primary_emotion": "平静", "primary_score": 0.0,
            "has_secondary_emotion": False, "emotion_intensity": 0.0,
            "positive_score": 0.0, "negative_score": 0.0, "sentiment_polarity": 0.0,
            "has_negation": False, "has_intensifier": False, "has_diminisher": False,
            "lexical_diversity": 0.0,
        }

    text = text.strip()
    features = {}

    # 基础统计
    features["char_count"] = len(text)
    sentences = re.split(r'[。！？!?\n]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    features["sentence_count"] = len(sentences) or 1
    features["avg_sentence_length"] = round(features["char_count"] / features["sentence_count"], 1)

    # 词汇多样性（基于字符级）
    chars = re.findall(r'[\u4e00-\u9fff]', text)
    if chars:
        features["lexical_diversity"] = round(len(set(chars)) / len(chars), 3)
    else:
        features["lexical_diversity"] = 0.0

    # 情绪词汇检测
    hits = _find_emotion_words(text)
    emotion_scores = {emo: 0.0 for emo in EMOTION_LEXICON}
    has_neg = False
    has_intens = False
    has_dimin = False

    for pos, emotion, weight, matched_word in hits:
        negated, mod_mult = _check_modifier(text, pos)
        if negated:
            has_neg = True
            mapped_emotion = EMOTION_NEGATION_MAP.get(emotion, emotion)
            emotion_scores[mapped_emotion] += weight * 0.6 * mod_mult
        else:
            emotion_scores[emotion] += weight * mod_mult

        if mod_mult > 1.0:
            has_intens = True
        elif mod_mult < 1.0 and mod_mult > 0:
            has_dimin = True

    features["emotion_scores"] = {k: round(v, 2) for k, v in emotion_scores.items()}
    features["has_negation"] = has_neg
    features["has_intensifier"] = has_intens
    features["has_diminisher"] = has_dimin

    # 主要情绪
    if any(emotion_scores.values()):
        primary = max(emotion_scores, key=emotion_scores.get)
        features["primary_emotion"] = primary
        features["primary_score"] = round(emotion_scores[primary], 2)

        # 次要情绪
        sorted_emos = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_emos) >= 2 and sorted_emos[1][1] > 0:
            features["secondary_emotion"] = sorted_emos[1][0]
            features["secondary_score"] = round(sorted_emos[1][1], 2)
            features["has_secondary_emotion"] = True
        else:
            features["secondary_emotion"] = None
            features["secondary_score"] = 0.0
            features["has_secondary_emotion"] = False
    else:
        features["primary_emotion"] = "平静"
        features["primary_score"] = 0.5
        features["secondary_emotion"] = None
        features["secondary_score"] = 0.0
        features["has_secondary_emotion"] = False

    # 总情绪强度
    features["emotion_intensity"] = round(sum(emotion_scores.values()), 2)

    # 正负面得分
    features["positive_score"] = round(emotion_scores["开心"] + emotion_scores["放松"] + emotion_scores["平静"] * 0.5, 2)
    features["negative_score"] = round(emotion_scores["低落"] + emotion_scores["焦虑"] + emotion_scores["疲惫"], 2)

    # 情感极性 (-1 到 1)
    total = features["positive_score"] + features["negative_score"]
    if total > 0:
        features["sentiment_polarity"] = round(
            (features["positive_score"] - features["negative_score"]) / total, 3
        )
    else:
        features["sentiment_polarity"] = 0.0

    return features


def analyze_emotion(text):
    """增强版情绪分析 — 替代旧版简单关键词匹配

    Args:
        text: 日记文本

    Returns:
        {
            "emotion": str,          # 主要情绪（向后兼容）
            "emotion_scores": dict,   # 六情绪完整分布
            "intensity": float,       # 情绪强度
            "secondary_emotion": str, # 次要情绪
            "sentiment_polarity": float, # 情感极性
            "text_stats": dict        # 文本统计
        }
    """
    features = extract_text_features(text)

    return {
        "emotion": features["primary_emotion"],
        "emotion_scores": features["emotion_scores"],
        "intensity": features["emotion_intensity"],
        "secondary_emotion": features.get("secondary_emotion"),
        "sentiment_polarity": features["sentiment_polarity"],
        "text_stats": {
            "char_count": features["char_count"],
            "sentence_count": features["sentence_count"],
            "avg_sentence_length": features["avg_sentence_length"],
            "lexical_diversity": features["lexical_diversity"],
            "has_negation": features["has_negation"],
        }
    }


def extract_diary_features(checkins):
    """从多条打卡记录中聚合日记文本特征（供 MSF-XGBoost 使用）

    Args:
        checkins: list of CheckIn ORM objects

    Returns:
        dict of aggregated text features
    """
    contents = [c.content for c in checkins if c.content and c.content.strip()]
    n = len(contents)

    if n == 0:
        return {
            "total_diary_entries": 0, "avg_char_count": 0, "total_chars": 0,
            "avg_positive_score": 0, "avg_negative_score": 0,
            "avg_sentiment_polarity": 0, "avg_emotion_intensity": 0,
            "dominant_emotion_ratio": 0, "negation_ratio": 0,
            "avg_lexical_diversity": 0, "text_engagement_score": 0,
        }

    all_features = [extract_text_features(t) for t in contents]

    char_counts = [f["char_count"] for f in all_features]
    pos_scores = [f["positive_score"] for f in all_features]
    neg_scores = [f["negative_score"] for f in all_features]
    polarities = [f["sentiment_polarity"] for f in all_features]
    intensities = [f["emotion_intensity"] for f in all_features]
    diversities = [f["lexical_diversity"] for f in all_features]
    negations = [1 if f["has_negation"] else 0 for f in all_features]

    # 主导情绪统计
    primary_emotions = [f["primary_emotion"] for f in all_features]
    from collections import Counter
    emo_counts = Counter(primary_emotions)

    return {
        "total_diary_entries": n,
        "avg_char_count": round(sum(char_counts) / n, 1),
        "total_chars": sum(char_counts),
        "avg_positive_score": round(sum(pos_scores) / n, 3),
        "avg_negative_score": round(sum(neg_scores) / n, 3),
        "avg_sentiment_polarity": round(sum(polarities) / n, 3),
        "avg_emotion_intensity": round(sum(intensities) / n, 3),
        "dominant_emotion": emo_counts.most_common(1)[0][0] if emo_counts else "平静",
        "dominant_emotion_ratio": round(emo_counts.most_common(1)[0][1] / n, 3) if emo_counts else 0,
        "negation_ratio": round(sum(negations) / n, 3),
        "avg_lexical_diversity": round(sum(diversities) / n, 3),
        "text_engagement_score": round(min(1.0, (sum(char_counts) / max(n, 1)) / 200), 3),
    }
