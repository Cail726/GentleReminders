"""测试 interpret_dimension — 量表维度评分解释"""
from config import interpret_dimension


class TestInterpretDimension:
    def test_green_at_2_0(self):
        result = interpret_dimension(2.0)
        assert result["level"] == "green"

    def test_green_below_2(self):
        result = interpret_dimension(1.0)
        assert result["level"] == "green"

    def test_yellow_at_2_01(self):
        result = interpret_dimension(2.01)
        assert result["level"] == "yellow"

    def test_yellow_at_3_0(self):
        result = interpret_dimension(3.0)
        assert result["level"] == "yellow"

    def test_orange_at_3_01(self):
        result = interpret_dimension(3.01)
        assert result["level"] == "orange"

    def test_orange_at_4_0(self):
        result = interpret_dimension(4.0)
        assert result["level"] == "orange"

    def test_red_at_4_01(self):
        result = interpret_dimension(4.01)
        assert result["level"] == "red"

    def test_red_at_5_0(self):
        result = interpret_dimension(5.0)
        assert result["level"] == "red"

    def test_out_of_range_low(self):
        result = interpret_dimension(-1.0)
        assert result["level"] == "green"

    def test_out_of_range_high(self):
        result = interpret_dimension(100.0)
        assert result["level"] == "red"

    def test_returns_all_keys(self):
        result = interpret_dimension(2.5)
        assert "level" in result
        assert "label" in result
        assert "desc" in result
