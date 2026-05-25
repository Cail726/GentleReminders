"""API 集成测试 — 注册、登录、登出"""


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/register", data={
            "username": "newuser", "password": "newpass123", "nickname": "新用户"
        })
        data = resp.json()
        assert data["code"] == 200

    def test_register_short_username(self, client):
        resp = client.post("/api/register", data={
            "username": "a", "password": "123456"
        })
        assert resp.json()["code"] == 400

    def test_register_short_password(self, client):
        resp = client.post("/api/register", data={
            "username": "validuser", "password": "123"
        })
        assert resp.json()["code"] == 400

    def test_register_duplicate_username(self, client, sample_user):
        resp = client.post("/api/register", data={
            "username": "testuser", "password": "123456"
        })
        assert resp.json()["code"] == 400


class TestLogin:
    def test_login_success(self, client, sample_user):
        resp = client.post("/api/login", data={
            "username": "testuser", "password": "test123"
        })
        assert resp.json()["code"] == 200

    def test_login_wrong_password(self, client, sample_user):
        resp = client.post("/api/login", data={
            "username": "testuser", "password": "wrongpassword"
        })
        assert resp.json()["code"] == 400

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/login", data={
            "username": "noone", "password": "123456"
        })
        assert resp.json()["code"] == 400


class TestUserInfo:
    def test_info_returns_user_data(self, auth_client):
        resp = auth_client.get("/api/user/info")
        data = resp.json()
        assert "id" in data
        assert data["username"] == "testuser"

    def test_info_requires_auth(self, client):
        resp = client.get("/api/user/info", follow_redirects=False)
        assert resp.status_code == 302
