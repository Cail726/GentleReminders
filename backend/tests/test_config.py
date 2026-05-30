"""测试 config.py — 常量配置的完整性和正确性"""
from config import (
    VALID_EMOTIONS, MOOD_SCORE, SCALE_QUESTIONS,
    SCALE_DIMENSION_ORDER, LETTER_TEMPLATES, AI_MESSAGES
)


class TestValidEmotions:
    def test_has_six_items(self):
        assert len(VALID_EMOTIONS) == 6

    def test_expected_emotions_present(self):
        assert VALID_EMOTIONS == {"开心", "放松", "平静", "低落", "焦虑", "疲惫"}


class TestMoodScore:
    def test_all_emotions_have_scores(self):
        for e in VALID_EMOTIONS:
            assert e in MOOD_SCORE, f"Missing mood score for {e}"

    def test_scores_in_range(self):
        for v in MOOD_SCORE.values():
            assert 1 <= v <= 5


class TestScaleQuestions:
    def test_exactly_25_questions(self):
        assert len(SCALE_QUESTIONS) == 25

    def test_ids_are_1_to_25(self):
        ids = [q["id"] for q in SCALE_QUESTIONS]
        assert ids == list(range(1, 26))

    def test_five_questions_per_dimension(self):
        for dim in SCALE_DIMENSION_ORDER:
            count = sum(1 for q in SCALE_QUESTIONS if q["dimension"] == dim)
            assert count == 5, f"Dimension {dim} has {count} questions, expected 5"

    def test_all_dimensions_present(self):
        dims = set(q["dimension"] for q in SCALE_QUESTIONS)
        assert dims == set(SCALE_DIMENSION_ORDER)

    def test_each_question_has_required_keys(self):
        for q in SCALE_QUESTIONS:
            assert "id" in q
            assert "dimension" in q
            assert "text" in q
            assert "reverse" in q
            assert isinstance(q["reverse"], bool)

    def test_reverse_scoring_exists(self):
        """至少有一些题目是反向计分的"""
        reverse_count = sum(1 for q in SCALE_QUESTIONS if q["reverse"])
        assert reverse_count > 0


class TestDimensionOrder:
    def test_five_dimensions(self):
        assert len(SCALE_DIMENSION_ORDER) == 5


class TestLetterTemplates:
    def test_has_all_milestone_levels(self):
        assert list(LETTER_TEMPLATES.keys()) == [7, 21, 50, 100]

    def test_each_template_has_required_fields(self):
        for level, tmpl in LETTER_TEMPLATES.items():
            assert "title" in tmpl, f"Level {level} missing title"
            assert "intro" in tmpl, f"Level {level} missing intro"
            assert "sections" in tmpl, f"Level {level} missing sections"
            assert "closing" in tmpl, f"Level {level} missing closing"
            assert len(tmpl["sections"]) > 0, f"Level {level} has empty sections"


class TestAiMessages:
    def test_all_emotions_have_messages(self):
        for e in VALID_EMOTIONS:
            assert e in AI_MESSAGES, f"Missing AI messages for {e}"

    def test_each_emotion_has_multiple_messages(self):
        for msgs in AI_MESSAGES.values():
            assert len(msgs) >= 2, "Each emotion should have at least 2 messages"
