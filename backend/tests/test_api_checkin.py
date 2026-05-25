"""API 集成测试 — 签到、树成长、信件触发"""


class TestCheckin:
    def test_create_checkin(self, auth_client):
        resp = auth_client.post("/api/checkin", data={
            "emotion": "开心", "content": "测试打卡"
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
        auth_client.post("/api/checkin", data={"emotion": "开心"})
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
    def test_letter_triggers_at_level_5(self, auth_client, db):
        """设置树到 4 级 95 经验，下一次签到触发信件"""
        from models.models import Tree
        tree = db.query(Tree).filter(Tree.user_id == 1).first()
        if not tree:
            tree = Tree(user_id=1, level=1, exp=0, health=100)
            db.add(tree)
        tree.level = 4
        tree.exp = 95
        db.commit()

        resp = auth_client.post("/api/checkin", data={"emotion": "开心"})
        data = resp.json()
        assert data["tree_level"] >= 5
        assert "new_letter" in data

    def test_letters_list(self, auth_client):
        resp = auth_client.get("/api/letters")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
