"""测试基础设施 — 内存数据库 + TestClient + 样本数据"""
import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure model/ is on path for NLP and ML imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "model"))

from models.database import Base, get_db
import models.models  # noqa: F401 — 确保 ORM 模型注册到 Base.metadata

# 内存 SQLite（StaticPool 保证单线程测试可用）
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def reset_rate_limiter():
    """每个测试前清空登录限流记录"""
    from models.database import Base
    from sqlalchemy import text
    Base.metadata.create_all(bind=engine)
    # 手动建 login_attempts 表（不属 ORM Base）
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                ip TEXT NOT NULL,
                attempt_time REAL NOT NULL
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip)"))
        conn.execute(text("DELETE FROM login_attempts"))
        conn.commit()


@pytest.fixture(scope="function")
def db():
    """每个测试独立的数据厧会话"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """带内存 DB 的 TestClient"""
    from main import app
    from dependencies import verify_csrf, check_login_rate

    def override_get_db():
        yield db

    def skip_csrf():
        return None

    def skip_rate():
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_csrf] = skip_csrf
    app.dependency_overrides[check_login_rate] = skip_rate
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user(db):
    """创建测试用户并返回"""
    from models.models import User
    from auth import hash_password
    user = User(username="testuser", password=hash_password("test123"), nickname="测试")
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def auth_client(client, sample_user):
    """已登录的 TestClient"""
    client.post("/api/login", data={"username": "testuser", "password": "test123"})
    return client
