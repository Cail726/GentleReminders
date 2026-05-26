"""测试 scale / trends / AI / letter 路由"""


class TestScale:
    def test_get_questions(self, client):
        resp = client.get("/api/scale/questions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 25

    def test_submit_requires_auth(self, client):
        resp = client.post("/api/scale/submit", data={"answers": "1:3,2:4"}, follow_redirects=False)
        assert resp.status_code in (302, 307)

    def test_submit_invalid_format(self, auth_client):
        resp = auth_client.post("/api/scale/submit", data={"answers": "bad"})
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == 400

    def test_submit_incomplete(self, auth_client):
        resp = auth_client.post("/api/scale/submit", data={"answers": "1:3,2:4"})
        assert resp.status_code == 400

    def test_submit_and_history(self, auth_client):
        ans = ",".join(f"{i}:3" for i in range(1, 26))
        resp = auth_client.post("/api/scale/submit", data={"answers": ans})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_score"] > 0

        resp = auth_client.get("/api/scale/history")
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) == 1
        assert history[0]["total_score"] > 0

    def test_get_scale_result_not_found(self, auth_client):
        resp = auth_client.get("/api/scale/result/99999")
        assert resp.status_code == 404


class TestTrends:
    def test_emotion_trends_empty(self, auth_client):
        resp = auth_client.get("/api/trends/emotion")
        assert resp.status_code == 200
        data = resp.json()
        assert "daily_avg" in data


class TestAI:
    def test_ai_message(self, client):
        resp = client.get("/api/ai/message?emotion=开心")
        assert resp.status_code == 200
        data = resp.json()
        assert "msg" in data

    def test_ai_message_unknown_emotion(self, client):
        resp = client.get("/api/ai/message?emotion=不存在")
        assert resp.status_code == 200
        assert "msg" in resp.json()

    def test_analyze_emotion(self, client):
        resp = client.post("/api/ai/analyze-emotion", data={"text": "今天很开心"})
        assert resp.status_code == 200
        data = resp.json()
        assert "emotion" in data


class TestLetters:
    def test_letters_list_requires_auth(self, client):
        resp = client.get("/api/letters", follow_redirects=False)
        assert resp.status_code in (302, 307)

    def test_letters_list_empty(self, auth_client):
        resp = auth_client.get("/api/letters")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_letter_not_found(self, auth_client):
        resp = auth_client.get("/api/letter/99999")
        assert resp.status_code == 404
