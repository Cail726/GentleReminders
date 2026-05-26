"""测试 letter_service 和 admin 群体统计 API"""
from sqlalchemy.orm import Session
from models.models import CheckIn
from utils.letter_service import generate_letter


class TestLetterService:
    def test_tree_level_below_5_uses_first_template(self, db: Session):
        """tree_level < 5 不应该崩溃，返回第一封信"""
        from models.models import User
        from auth import hash_password
        user = User(username="lettertest", password=hash_password("test123"), nickname="信")
        db.add(user)
        db.commit()

        # 添加几条打卡记录
        for emo in ["开心", "低落", "平静"]:
            db.add(CheckIn(user_id=user.id, emotion=emo, content="测试"))
        db.commit()

        letter = generate_letter(user.id, 3, db)
        assert letter is not None
        assert letter.title != ""
        assert letter.content != ""

    def test_first_milestone_letter(self, db: Session):
        """tree_level 刚好达到 5 时应生成信件"""
        from models.models import User
        from auth import hash_password
        user = User(username="letter2", password=hash_password("test123"), nickname="信2")
        db.add(user)
        db.commit()

        for _ in range(5):
            db.add(CheckIn(user_id=user.id, emotion="开心", content="测试"))
        db.commit()

        letter = generate_letter(user.id, 5, db)
        assert letter.tree_level == 5
        assert letter.user_id == user.id


class TestAdminGroupStats:
    def test_emotion_count(self, client):
        resp = client.get("/api/admin/emotion-count", follow_redirects=False)
        assert resp.status_code in (302, 307)

    def test_daily_trend(self, client):
        resp = client.get("/api/admin/daily-trend", follow_redirects=False)
        assert resp.status_code in (302, 307)

    def test_risk_distribution(self, client):
        resp = client.get("/api/admin/risk-distribution", follow_redirects=False)
        assert resp.status_code in (302, 307)

    def test_hourly_distribution(self, client):
        resp = client.get("/api/admin/hourly-distribution", follow_redirects=False)
        assert resp.status_code in (302, 307)

    def test_old_checkin_endpoints_removed(self, client):
        """/api/admin/all-checkin 和 /api/admin/risk-user 应已移除"""
        assert client.get("/api/admin/all-checkin").status_code == 404
        assert client.get("/api/admin/risk-user").status_code == 404
