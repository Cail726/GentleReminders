"""测试 anonymize_user_id — 用户 ID 匿名化"""
from dependencies import anonymize_user_id


class TestAnonymizeUserId:
    def test_returns_string_starting_with_user(self):
        result = anonymize_user_id(1)
        assert result.startswith("用户")

    def test_total_length_is_8(self):
        """用户(2 chars) + 6 hex chars = 8"""
        result = anonymize_user_id(1)
        assert len(result) == 8

    def test_deterministic(self):
        assert anonymize_user_id(42) == anonymize_user_id(42)

    def test_different_ids_different_results(self):
        assert anonymize_user_id(1) != anonymize_user_id(2)

    def test_zero_id(self):
        result = anonymize_user_id(0)
        assert result.startswith("用户")

    def test_large_id(self):
        result = anonymize_user_id(999999)
        assert len(result) == 8
