"""MSF-XGBoost 多源特征融合 — 特征提取管道"""
import math
from datetime import date, timedelta
from collections import Counter
from text_features import extract_diary_features

MOOD_SCORE = {"开心": 5, "放松": 4, "平静": 3, "低落": 2, "焦虑": 1, "疲惫": 1}


def extract_features(checkins, scale_records):
    """从打卡记录和量表数据中提取多源特征

    Args:
        checkins: list of CheckIn ORM objects (sorted by time asc)
        scale_records: list of ScaleResponse ORM objects

    Returns:
        dict of feature_name -> float value
    """
    features = {}

    # =========== 情绪打卡特征 ===========
    if checkins:
        scores = [MOOD_SCORE.get(c.emotion, 3) for c in checkins]
        n = len(scores)
        mean_score = sum(scores) / n
        variance = sum((s - mean_score) ** 2 for s in scores) / n

        emotions = [c.emotion for c in checkins]
        emotion_counts = Counter(emotions)
        neg_count = emotion_counts.get("低落", 0) + emotion_counts.get("焦虑", 0) + emotion_counts.get("疲惫", 0)
        pos_count = emotion_counts.get("开心", 0) + emotion_counts.get("放松", 0)

        features["total_checkins"] = float(n)
        features["avg_mood_score"] = round(mean_score, 3)
        features["mood_variance"] = round(variance, 3)
        features["mood_std"] = round(math.sqrt(variance), 3)
        features["emotion_diversity"] = round(len(emotion_counts) / 6.0, 3)
        features["negative_ratio"] = round(neg_count / n, 3)
        features["positive_ratio"] = round(pos_count / n, 3)

        # 近期趋势（近7天 vs 总体）
        cutoff = date.today() - timedelta(days=7)
        recent_scores = [MOOD_SCORE.get(c.emotion, 3) for c in checkins
                         if c.create_time.date() >= cutoff]
        if recent_scores:
            recent_avg = sum(recent_scores) / len(recent_scores)
            features["recent_avg_7d"] = round(recent_avg, 3)
            features["trend_delta"] = round(recent_avg - mean_score, 3)
        else:
            features["recent_avg_7d"] = round(mean_score, 3)
            features["trend_delta"] = 0.0

        # 打卡规律性
        if n >= 2:
            dates = sorted([c.create_time.date() for c in checkins])
            gaps = []
            for i in range(1, len(dates)):
                gaps.append((dates[i] - dates[i-1]).days)
            avg_gap = sum(gaps) / len(gaps)
            gap_variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
            features["checkin_regularity"] = round(1.0 / (1.0 + math.sqrt(gap_variance)), 3)
            features["avg_gap_days"] = round(avg_gap, 3)
        else:
            features["checkin_regularity"] = 0.0
            features["avg_gap_days"] = 7.0

        # 连续打卡
        all_dates = set(c.create_time.date() for c in checkins)
        today = date.today()
        streak = 0
        for i in range(30):
            check_date = today - timedelta(days=i)
            if check_date in all_dates:
                streak += 1
            else:
                break
        features["current_streak"] = float(streak)

        # 距上次打卡天数
        last_date = max(all_dates)
        features["days_since_last"] = float((today - last_date).days)

        # 周打卡频率
        features["weekly_frequency"] = round(n / max(1, (today - min(all_dates)).days / 7.0), 2)
    else:
        # 无打卡记录时的默认值
        for key in ["total_checkins", "avg_mood_score", "mood_variance", "mood_std",
                     "emotion_diversity", "negative_ratio", "positive_ratio",
                     "recent_avg_7d", "trend_delta", "checkin_regularity",
                     "avg_gap_days", "current_streak", "days_since_last", "weekly_frequency"]:
            features[key] = 0.0

    # =========== 日记文本特征（增强 NLP） ===========
    diary_features = extract_diary_features(checkins)
    features.update(diary_features)

    # =========== 量表特征 ===========
    if scale_records:
        latest = scale_records[0]
        import json
        dim_scores = json.loads(latest.dimension_scores) if isinstance(latest.dimension_scores, str) else {}
        for dim, score in dim_scores.items():
            features[f"scale_{dim}"] = round(score, 2)
        features["scale_total"] = round(latest.total_score, 2)
        features["scale_count"] = float(len(scale_records))
        if dim_scores:
            features["scale_max_dim"] = round(max(dim_scores.values()), 2)
            features["scale_min_dim"] = round(min(dim_scores.values()), 2)
            features["scale_range"] = round(features["scale_max_dim"] - features["scale_min_dim"], 2)
    else:
        for dim in ["焦虑感受", "情绪状态", "社交状态", "压力与疲惫", "睡眠质量"]:
            features[f"scale_{dim}"] = 0.0
        features["scale_total"] = 0.0
        features["scale_count"] = 0.0
        features["scale_max_dim"] = 0.0
        features["scale_min_dim"] = 0.0
        features["scale_range"] = 0.0

    return features


FEATURE_NAMES = [
    "total_checkins", "avg_mood_score", "mood_variance", "mood_std",
    "emotion_diversity", "negative_ratio", "positive_ratio",
    "recent_avg_7d", "trend_delta", "checkin_regularity",
    "avg_gap_days", "current_streak", "days_since_last", "weekly_frequency",
    "total_diary_entries", "avg_char_count", "total_chars",
    "avg_positive_score", "avg_negative_score", "avg_sentiment_polarity",
    "avg_emotion_intensity", "dominant_emotion_ratio", "negation_ratio",
    "avg_lexical_diversity", "text_engagement_score",
    "scale_焦虑感受", "scale_情绪状态", "scale_社交状态", "scale_压力与疲惫", "scale_睡眠质量",
    "scale_total", "scale_count", "scale_max_dim", "scale_min_dim", "scale_range",
]
