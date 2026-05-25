"""测试 train.py 中的纯函数 — 评分解读、建议生成、置信度"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "model"))

from train import _score_level, _confidence, _generate_suggestions, _feature_summary


class TestScoreLevel:
    def test_green_at_75(self):
        assert _score_level(75)["level"] == "green"

    def test_green_at_100(self):
        assert _score_level(100)["level"] == "green"

    def test_yellow_at_74(self):
        assert _score_level(74)["level"] == "yellow"

    def test_yellow_at_55(self):
        assert _score_level(55)["level"] == "yellow"

    def test_yellow_at_74_point_9(self):
        assert _score_level(74.9)["level"] == "yellow"

    def test_orange_at_54(self):
        assert _score_level(54)["level"] == "orange"

    def test_orange_at_35(self):
        assert _score_level(35)["level"] == "orange"

    def test_red_at_34(self):
        assert _score_level(34)["level"] == "red"

    def test_red_at_0(self):
        assert _score_level(0)["level"] == "red"

    def test_returns_dict_with_keys(self):
        r = _score_level(60)
        assert all(k in r for k in ["level", "label", "desc"])


class TestConfidence:
    def test_insufficient_zero(self):
        assert _confidence({"total_checkins": 0}) == "insufficient"

    def test_insufficient_two(self):
        assert _confidence({"total_checkins": 2}) == "insufficient"

    def test_low_three(self):
        assert _confidence({"total_checkins": 3}) == "low"

    def test_low_six(self):
        assert _confidence({"total_checkins": 6}) == "low"

    def test_medium_seven(self):
        assert _confidence({"total_checkins": 7}) == "medium"

    def test_medium_nineteen(self):
        assert _confidence({"total_checkins": 19}) == "medium"

    def test_high_twenty(self):
        assert _confidence({"total_checkins": 20}) == "high"

    def test_high_many(self):
        assert _confidence({"total_checkins": 999}) == "high"

    def test_missing_key_defaults_zero(self):
        assert _confidence({}) == "insufficient"


class TestGenerateSuggestions:
    def test_all_good(self):
        dims = {"emotional_stability": {"score": 80}, "social_engagement": {"score": 75}}
        features = {"total_checkins": 10}
        result = _generate_suggestions(dims, features)
        assert isinstance(result, list)

    def test_some_low(self):
        dims = {"emotional_stability": {"score": 30}, "social_engagement": {"score": 80}}
        features = {"total_checkins": 10}
        result = _generate_suggestions(dims, features)
        assert len(result) > 0

    def test_low_checkins_adds_data_tip(self):
        dims = {"emotional_stability": {"score": 30}}
        features = {"total_checkins": 3}
        result = _generate_suggestions(dims, features)
        assert any("打卡记录" in s for s in result)


class TestFeatureSummary:
    def test_basic_output(self):
        features = {"total_checkins": 10, "avg_mood_score": 3.5, "current_streak": 3, "scale_count": 1}
        result = _feature_summary(features)
        assert result["total_checkins"] == 10
        assert result["has_scale_data"] is True

    def test_no_scale_data(self):
        features = {"total_checkins": 5, "avg_mood_score": 4.0, "current_streak": 0, "scale_count": 0}
        result = _feature_summary(features)
        assert result["has_scale_data"] is False

    def test_missing_keys_default(self):
        result = _feature_summary({})
        assert result["total_checkins"] == 0
