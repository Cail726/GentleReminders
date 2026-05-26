"""MSF-XGBoost 多源特征融合模型 — 训练与推理

模型输出5个心理健康维度评分（0-100），仅用于状态描述，不构成诊断。
"""
import os
import pickle
import numpy as np
from xgboost import XGBRegressor
from sklearn.multioutput import MultiOutputRegressor

from features import extract_features, FEATURE_NAMES

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(MODEL_DIR, "msf_xgb_model.pkl")

OUTPUT_DIMENSIONS = [
    "emotional_stability",   # 情绪稳定性
    "social_engagement",     # 社交参与度
    "stress_resilience",     # 压力承受力
    "sleep_quality",         # 睡眠质量
    "overall_wellbeing",     # 综合心理健康指数
]

DIM_LABELS_ZH = {
    "emotional_stability": "情绪稳定性",
    "social_engagement": "社交参与度",
    "stress_resilience": "压力承受力",
    "sleep_quality": "睡眠质量",
    "overall_wellbeing": "综合心理健康指数",
}

DIM_DESCRIPTIONS = {
    "emotional_stability": "反映情绪波动程度和负面情绪的调节能力。分数越高表示情绪越稳定。",
    "social_engagement": "反映社交互动的积极性和人际连接的紧密程度。分数越高表示社交状态越好。",
    "stress_resilience": "反映面对学习和生活压力时的承受和恢复能力。分数越高表示抗压能力越强。",
    "sleep_quality": "反映睡眠的规律性和休息质量。分数越高表示睡眠状态越好。",
    "overall_wellbeing": "综合反映当前心理健康的整体水平，由以上四个维度加权综合得出。",
}


def _generate_synthetic_data(n_samples=2000):
    """基于心理学启发式规则生成合成训练数据"""
    rng = np.random.default_rng(42)

    X = np.zeros((n_samples, len(FEATURE_NAMES)))
    Y = np.zeros((n_samples, len(OUTPUT_DIMENSIONS)))

    for i in range(n_samples):
        # --- 打卡行为特征 ---
        total_checkins = rng.uniform(0, 60)
        avg_mood = rng.uniform(1, 5)
        mood_var = rng.uniform(0, 4)
        mood_std = np.sqrt(mood_var)
        emotion_div = rng.uniform(0.1, 1.0)
        neg_ratio = rng.beta(2, 5)  # skewed low
        pos_ratio = rng.beta(3, 3)
        recent_avg = avg_mood + rng.uniform(-1, 1)
        recent_avg = np.clip(recent_avg, 1, 5)
        trend_delta = recent_avg - avg_mood
        regularity = rng.uniform(0, 1)
        avg_gap = rng.uniform(0.5, 14)
        streak = rng.integers(0, 30)
        days_since = rng.integers(0, 14)
        weekly_freq = rng.uniform(0, 10)

        # --- 增强文本特征 ---
        total_diary = max(0, int(total_checkins * rng.uniform(0.2, 0.9)))
        avg_char = rng.uniform(10, 300) if total_diary > 0 else 0
        total_chars = total_diary * avg_char
        avg_pos = rng.uniform(0, 5)
        avg_neg = rng.uniform(0, 5)
        avg_polarity = rng.uniform(-1, 1)
        avg_intensity = rng.uniform(0, 10)
        dominant_ratio = rng.uniform(0.2, 0.8)
        negation_r = rng.uniform(0, 0.4)
        lex_div = rng.uniform(0.2, 0.9)
        text_engage = min(1.0, avg_char / 200)

        # --- 量表特征 ---
        has_scale = rng.random() > 0.3
        if has_scale:
            scale_anxiety = rng.uniform(1, 5)
            scale_mood = rng.uniform(1, 5)
            scale_social = rng.uniform(1, 5)
            scale_stress = rng.uniform(1, 5)
            scale_sleep = rng.uniform(1, 5)
            scale_total = (scale_anxiety + scale_mood + scale_social + scale_stress + scale_sleep) / 5
            scale_count = rng.integers(1, 5)
            scale_max = max(scale_anxiety, scale_mood, scale_social, scale_stress, scale_sleep)
            scale_min = min(scale_anxiety, scale_mood, scale_social, scale_stress, scale_sleep)
            scale_range = scale_max - scale_min
        else:
            scale_anxiety = scale_mood = scale_social = scale_stress = scale_sleep = 0
            scale_total = scale_count = scale_max = scale_min = scale_range = 0.0

        # 组装特征向量 — 通过 dict 保证与 FEATURE_NAMES 严格对齐
        feat = {
            "total_checkins": total_checkins, "avg_mood_score": avg_mood,
            "mood_variance": mood_var, "mood_std": mood_std,
            "emotion_diversity": emotion_div, "negative_ratio": neg_ratio,
            "positive_ratio": pos_ratio, "recent_avg_7d": recent_avg,
            "trend_delta": trend_delta, "checkin_regularity": regularity,
            "avg_gap_days": avg_gap, "current_streak": streak,
            "days_since_last": days_since, "weekly_frequency": weekly_freq,
            "total_diary_entries": total_diary, "avg_char_count": avg_char,
            "total_chars": total_chars,
            "avg_positive_score": avg_pos, "avg_negative_score": avg_neg,
            "avg_sentiment_polarity": avg_polarity,
            "avg_emotion_intensity": avg_intensity,
            "dominant_emotion_ratio": dominant_ratio,
            "negation_ratio": negation_r, "avg_lexical_diversity": lex_div,
            "text_engagement_score": text_engage,
            "scale_焦虑感受": scale_anxiety, "scale_情绪状态": scale_mood,
            "scale_社交状态": scale_social, "scale_压力与疲惫": scale_stress,
            "scale_睡眠质量": scale_sleep,
            "scale_total": scale_total, "scale_count": scale_count,
            "scale_max_dim": scale_max, "scale_min_dim": scale_min,
            "scale_range": scale_range,
        }
        X[i] = [feat[name] for name in FEATURE_NAMES]

        # --- 启发式标签生成 ---
        emo_stab = 50.0
        emo_stab += (avg_mood - 3.0) * 12
        emo_stab -= mood_var * 5
        emo_stab -= neg_ratio * 25
        emo_stab += trend_delta * 8
        emo_stab += avg_polarity * 8                    # 情感极性 → 稳定
        if has_scale:
            emo_stab -= (scale_anxiety - 3.0) * 4
            emo_stab -= (scale_mood - 3.0) * 4
        emo_stab += rng.normal(0, 5)

        social = 50.0
        social += regularity * 15
        social += streak * 0.5
        social += emotion_div * 10
        social += text_engage * 8                       # 文本投入度 → 社交
        social -= (days_since / 14.0) * 15
        if has_scale:
            social -= (scale_social - 3.0) * 5
        social += rng.normal(0, 5)

        stress = 50.0
        stress -= neg_ratio * 20
        stress += weekly_freq * 2
        stress += trend_delta * 6
        stress += regularity * 12
        stress += avg_polarity * 5                     # 正面情绪 → 压力承受力
        stress -= avg_intensity * 1.5                  # 情绪强度过高 → 压力
        if has_scale:
            stress -= (scale_stress - 3.0) * 5
        stress += rng.normal(0, 5)

        sleep = 50.0
        sleep += regularity * 10
        sleep -= (avg_gap / 14.0) * 20
        sleep -= (days_since / 14.0) * 15
        sleep -= avg_neg * 3                           # 负面情绪多 → 影响睡眠
        if has_scale:
            sleep -= (scale_sleep - 3.0) * 6
        sleep += rng.normal(0, 5)

        # overall_wellbeing: 综合加权
        overall = (
            emo_stab * 0.35 +
            social * 0.20 +
            stress * 0.25 +
            sleep * 0.20
        )
        if total_checkins < 3:
            overall -= 10  # 数据太少，置信度降低

        Y[i] = [
            np.clip(emo_stab, 0, 100),
            np.clip(social, 0, 100),
            np.clip(stress, 0, 100),
            np.clip(sleep, 0, 100),
            np.clip(overall, 0, 100),
        ]

    return X, Y


def train_model(force=False):
    """训练 MSF-XGBoost 模型（含 train/test split + 评估指标）"""
    if not force and os.path.exists(MODEL_PATH):
        return

    print("[MSF-XGB] 生成合成训练数据...")
    X, Y = _generate_synthetic_data(2000)

    # 80/20 train/test split
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    Y_train, Y_test = Y[:split_idx], Y[split_idx:]

    print(f"[MSF-XGB] 训练多输出回归模型 (特征数={X.shape[1]}, 训练={X_train.shape[0]}, 测试={X_test.shape[0]})...")
    base_model = XGBRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )
    model = MultiOutputRegressor(base_model)
    model.fit(X_train, Y_train)

    # 评估
    Y_pred = model.predict(X_test)
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    print("[MSF-XGB] 测试集评估结果:")
    for i, dim in enumerate(OUTPUT_DIMENSIONS):
        mae = mean_absolute_error(Y_test[:, i], Y_pred[:, i])
        rmse = np.sqrt(mean_squared_error(Y_test[:, i], Y_pred[:, i]))
        r2 = r2_score(Y_test[:, i], Y_pred[:, i])
        print(f"  {dim}: MAE={mae:.2f}, RMSE={rmse:.2f}, R²={r2:.3f}")

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"[MSF-XGB] 模型已保存至 {MODEL_PATH}")


def load_model():
    """加载训练好的模型"""
    if not os.path.exists(MODEL_PATH):
        train_model()
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict(checkins, scale_records):
    """运行 MSF-XGBoost 推理

    Args:
        checkins: list of CheckIn ORM objects
        scale_records: list of ScaleResponse ORM objects

    Returns:
        dict with dimension scores, interpretations, and suggestions
    """
    features_dict = extract_features(checkins, scale_records)
    feature_vector = np.array([[features_dict.get(name, 0.0) for name in FEATURE_NAMES]])

    model = load_model()
    raw_scores = model.predict(feature_vector)[0]

    dim_scores = {}
    for dim, score in zip(OUTPUT_DIMENSIONS, raw_scores):
        dim_scores[dim] = {
            "score": round(float(score), 1),
            "label": DIM_LABELS_ZH[dim],
            "description": DIM_DESCRIPTIONS[dim],
            "level": _score_level(float(score)),
        }

    suggestions = _generate_suggestions(dim_scores, features_dict)

    return {
        "dimension_scores": dim_scores,
        "suggestions": suggestions,
        "feature_summary": _feature_summary(features_dict),
        "data_confidence": _confidence(features_dict),
    }


def _score_level(score):
    if score >= 75:
        return {"level": "green", "label": "良好", "desc": "该维度表现良好，请继续保持。"}
    elif score >= 55:
        return {"level": "yellow", "label": "一般", "desc": "该维度处于中等水平，有提升空间。"}
    elif score >= 35:
        return {"level": "orange", "label": "偏低", "desc": "该维度评分偏低，建议关注并尝试调整。"}
    else:
        return {"level": "red", "label": "需要关注", "desc": "该维度评分较低，建议主动寻求支持和改善。"}


def _generate_suggestions(dim_scores, features):
    """基于维度得分和特征生成描述性建议"""
    suggestions = []
    low_dims = [dim for dim, info in dim_scores.items() if info["score"] < 55]

    if not low_dims:
        suggestions.append("你的各项心理指标表现良好，请继续保持当前的生活节奏和自我关怀习惯。")
        return suggestions

    dim_tips = {
        "emotional_stability": "尝试每天花5分钟做深呼吸练习，或记录下让自己开心的小事。情绪日记有助于提升情绪觉察力。",
        "social_engagement": "可以从小事开始增加社交——给朋友发条消息、参加一次社团活动、或在课堂上主动发言。",
        "stress_resilience": "合理安排学习和休息时间，尝试把大任务拆分成小步骤。适量运动和听音乐也有助于缓解压力。",
        "sleep_quality": "尽量保持固定的作息时间，睡前1小时减少手机使用，可以尝试听轻音乐或白噪音帮助入睡。",
        "overall_wellbeing": "心理健康是一个持续关注的过程，建议从最想改善的一个维度开始，逐步建立健康的日常习惯。",
    }

    # 选取最低的2-3个维度给出建议
    for dim in sorted(low_dims, key=lambda d: dim_scores[d]["score"])[:3]:
        label = DIM_LABELS_ZH[dim]
        suggestions.append(f"【{label}】{dim_tips.get(dim, '建议关注并适当调整。')}")

    # 如果数据量很少，增加采集建议
    if features.get("total_checkins", 0) < 5:
        suggestions.append("💡 提示：当前打卡记录较少，评估结果仅供参考。坚持每日打卡可以获得更准确的分析。")

    return suggestions


def _feature_summary(features):
    """生成特征摘要"""
    return {
        "total_checkins": int(features.get("total_checkins", 0)),
        "avg_mood_score": round(features.get("avg_mood_score", 0), 1),
        "current_streak": int(features.get("current_streak", 0)),
        "has_scale_data": features.get("scale_count", 0) > 0,
    }


def _confidence(features):
    """评估当前数据的置信度"""
    n = features.get("total_checkins", 0)
    if n >= 20:
        return "high"
    elif n >= 7:
        return "medium"
    elif n >= 3:
        return "low"
    else:
        return "insufficient"


# 首次导入时自动训练模型
if __name__ == "__main__":
    train_model(force=True)
