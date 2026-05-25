"""测试 text_features.py — NLP 情绪分析引擎"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "model"))

from text_features import (
    _find_emotion_words, _check_modifier,
    extract_text_features, analyze_emotion, extract_diary_features
)


class TestFindEmotionWords:
    def test_finds_single_word(self):
        hits = _find_emotion_words("我今天很开心")
        assert len(hits) > 0
        emotions = [h[1] for h in hits]
        assert "开心" in emotions

    def test_no_match_returns_empty(self):
        hits = _find_emotion_words("今天天气晴朗万里无云")
        assert hits == []

    def test_empty_text_returns_empty(self):
        hits = _find_emotion_words("")
        assert hits == []

    def test_finds_multiple_emotions(self):
        hits = _find_emotion_words("又开心又有点难过")
        emotions = set(h[1] for h in hits)
        assert "开心" in emotions
        assert "低落" in emotions  # "难过" is in 低落

    def test_sorted_by_position(self):
        hits = _find_emotion_words("我很开心但是也很焦虑")
        positions = [h[0] for h in hits]
        assert positions == sorted(positions)


class TestCheckModifier:
    def test_no_modifier(self):
        negated, mult = _check_modifier("开心", 0)
        assert negated is False
        assert mult == 1.0

    def test_intensifier(self):
        negated, mult = _check_modifier("很开心", 1)
        assert negated is False
        assert mult == 1.5

    def test_diminisher(self):
        negated, mult = _check_modifier("有点累", 2)
        assert negated is False
        assert mult == 0.5

    def test_negation(self):
        negated, mult = _check_modifier("不开心", 1)
        assert negated is True

    def test_negation_immediately_before_emotion(self):
        """否定词紧邻情绪词时正确识别"""
        negated, mult = _check_modifier("不开心", 1)
        assert negated is True

    def test_intensifier_without_negation(self):
        """无否定时正确识别程度词"""
        negated, mult = _check_modifier("很开心", 1)
        assert negated is False
        assert mult == 1.5


class TestExtractTextFeatures:
    def test_empty_text_returns_defaults(self):
        result = extract_text_features("")
        assert result["char_count"] == 0
        assert result["emotion_intensity"] == 0.0

    def test_none_text_returns_defaults(self):
        result = extract_text_features(None)
        assert result["primary_emotion"] == "平静"

    def test_happy_text(self):
        result = extract_text_features("今天很开心")
        assert result["primary_emotion"] == "开心"
        assert result["primary_score"] > 0

    def test_sad_text(self):
        result = extract_text_features("我很难过很伤心")
        assert result["primary_emotion"] == "低落"
        assert result["sentiment_polarity"] < 0

    def test_polarity_positive(self):
        result = extract_text_features("非常开心非常快乐")
        assert result["sentiment_polarity"] > 0

    def test_polarity_negative(self):
        result = extract_text_features("非常难过非常伤心")
        assert result["sentiment_polarity"] < 0

    def test_char_count(self):
        result = extract_text_features("Hello世界")
        assert result["char_count"] == 7

    def test_no_emotion_defaults_to_calm(self):
        result = extract_text_features("今天星期三")
        assert result["primary_emotion"] == "平静"


class TestAnalyzeEmotion:
    def test_returns_required_keys(self):
        result = analyze_emotion("我很开心")
        for key in ["emotion", "emotion_scores", "intensity", "sentiment_polarity", "text_stats"]:
            assert key in result, f"Missing key: {key}"

    def test_emotion_is_string(self):
        result = analyze_emotion("测试")
        assert isinstance(result["emotion"], str)

    def test_scores_are_dict(self):
        result = analyze_emotion("测试")
        assert isinstance(result["emotion_scores"], dict)


class TestExtractDiaryFeatures:
    def test_empty_list(self):
        result = extract_diary_features([])
        assert result["total_diary_entries"] == 0

    def test_single_entry(self):
        class FakeCheckin:
            content = "今天很开心"
        result = extract_diary_features([FakeCheckin()])
        assert result["total_diary_entries"] == 1
        assert result["dominant_emotion_ratio"] == 1.0

    def test_mixed_emotions(self):
        class C1:
            content = "开心的一天"
        class C2:
            content = "好难过啊"
        class C3:
            content = "开心快乐"
        result = extract_diary_features([C1(), C2(), C3()])
        assert result["total_diary_entries"] == 3
