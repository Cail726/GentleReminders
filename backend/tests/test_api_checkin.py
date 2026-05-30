"""API 集成测试 — 签到、树成长、信件触发"""


class TestCheckin:
    def test_create_checkin(self, auth_client):
        resp = auth_client.post("/api/checkin", data={
            "emotion": "开心", "content": "今天阳光很好，心情也跟着明亮起来"
        })
        data = resp.json()
        assert data["status"] == "ok"
        assert data["tree_level"] >= 1
        assert "tree_health" in data

    def test_invalid_emotion_rejected(self, auth_client):
        resp = auth_client.post("/api/checkin", data={
            "emotion": "愤怒", "content": "不应该成功"
        })
        assert resp.json()["code"] == 400

    def test_checkin_creates_tree(self, auth_client, db):
        """首次签到应该创建小树"""
        from models.models import Tree
        auth_client.post("/api/checkin", data={"emotion": "开心", "content": "第一次打卡，种下一颗种子"})
        tree = db.query(Tree).filter(Tree.user_id == 1).first()
        assert tree is not None
        assert tree.level >= 1

    def test_checkin_requires_auth(self, client):
        resp = client.post("/api/checkin", data={"emotion": "开心"}, follow_redirects=False)
        assert resp.status_code == 302


class TestTreeInfo:
    def test_tree_info(self, auth_client):
        resp = auth_client.get("/api/tree/info")
        data = resp.json()
        assert "level" in data
        assert "exp" in data
        assert "health" in data


class TestLetterTrigger:
    def test_letter_triggers_at_level_7(self, auth_client, db):
        """设置树为 6 级，下一次签到触发第一封信（7级里程碑）"""
        from models.models import Tree
        tree = db.query(Tree).filter(Tree.user_id == 1).first()
        if not tree:
            tree = Tree(user_id=1, level=1, exp=0, health=100)
            db.add(tree)
        tree.level = 6
        tree.exp = 90
        db.commit()

        resp = auth_client.post("/api/checkin", data={"emotion": "开心", "content": "第七片叶子了，树越来越茂盛"})
        data = resp.json()
        assert data["tree_level"] >= 7
        assert "new_letter" in data

    def test_letters_list(self, auth_client):
        resp = auth_client.get("/api/letters")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
