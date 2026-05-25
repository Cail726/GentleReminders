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

# 内存 SQLite（StaticPool 保证单线程测试可用）
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def reset_rate_limiter():
    """每个测试前清空登录限流计数器"""
    from dependencies import _login_attempts
    _login_attempts.clear()


@pytest.fixture(scope="function")
def db():
    """每个测试独立的数据库会话"""
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

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
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
