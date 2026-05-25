"""管理员 API 集成测试 — 登录、强制改密、权限控制"""
import pytest
from models.models import Admin
from auth import hash_password


@pytest.fixture
def sample_admin(db):
    admin = Admin(username="admin", password=hash_password("admin123"), must_change_password=True)
    db.add(admin)
    db.commit()
    return admin


@pytest.fixture
def admin_auth_client(client, db):
    """已改密后的管理员 TestClient"""
    admin = Admin(username="admin2", password=hash_password("admin456"), must_change_password=False)
    db.add(admin)
    db.commit()
    client.post("/api/admin/login", data={"username": "admin2", "password": "admin456"})
    return client


class TestAdminLogin:
    def test_login_success_but_must_change(self, client, sample_admin):
        resp = client.post("/api/admin/login", data={
            "username": "admin", "password": "admin123"
        })
        data = resp.json()
        assert data["code"] == 301
        assert data["redirect"] == "/admin/change-password"

    def test_login_success_no_redirect(self, admin_auth_client):
        resp = admin_auth_client.get("/api/admin/info")
        assert resp.json()["username"] == "admin2"

    def test_login_wrong_password(self, client, sample_admin):
        resp = client.post("/api/admin/login", data={
            "username": "admin", "password": "wrong"
        })
        assert resp.json()["code"] == 400


class TestAdminChangePassword:
    @pytest.fixture
    def must_change_client(self, client, sample_admin):
        """登录但尚未改密的管理员 client"""
        client.post("/api/admin/login", data={"username": "admin", "password": "admin123"})
        return client

    def test_change_password_success(self, must_change_client, db):
        resp = must_change_client.post("/api/admin/change-password", data={
            "old_password": "admin123", "new_password": "newpass666"
        })
        assert resp.json()["code"] == 200
        admin = db.query(Admin).filter(Admin.username == "admin").first()
        assert admin.must_change_password is False

    def test_change_password_wrong_old(self, must_change_client):
        resp = must_change_client.post("/api/admin/change-password", data={
            "old_password": "wrongold", "new_password": "newpass666"
        })
        assert resp.json()["code"] == 400

    def test_change_password_too_short(self, must_change_client):
        resp = must_change_client.post("/api/admin/change-password", data={
            "old_password": "admin123", "new_password": "123"
        })
        assert resp.json()["code"] == 400

    def test_cannot_access_index_before_change(self, must_change_client):
        resp = must_change_client.get("/admin/index", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("Location") == "/admin/change-password"

    def test_can_access_index_after_change(self, must_change_client, db):
        must_change_client.post("/api/admin/change-password", data={
            "old_password": "admin123", "new_password": "newpass666"
        })
        resp = must_change_client.get("/admin/index")
        assert resp.status_code == 200
