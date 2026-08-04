"""Token 鉴权中间件测试"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """无 AUTH_TOKEN 环境变量 → 鉴权关闭"""
    monkeypatch.delenv("AUTH_TOKEN", raising=False)
    from main import app
    return TestClient(app)


@pytest.fixture
def protected_client(monkeypatch):
    """设置了 AUTH_TOKEN → 鉴权开启"""
    monkeypatch.setenv("AUTH_TOKEN", "secret-token-123")
    from main import app
    return TestClient(app)


def test_no_auth_token_allows_all(client):
    """未配置 AUTH_TOKEN 时，所有请求放行"""
    resp = client.get("/api/books")
    assert resp.status_code == 200


def test_auth_token_blocks_missing_token(protected_client):
    """开启鉴权后，无 token 的 /api 请求返回 401"""
    resp = protected_client.get("/api/books")
    assert resp.status_code == 401
    assert "未授权" in resp.json()["detail"]


def test_auth_token_blocks_wrong_token(protected_client):
    """错误 token 返回 401"""
    resp = protected_client.get(
        "/api/books",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


def test_auth_token_accepts_correct_token(protected_client):
    """正确 token 放行"""
    resp = protected_client.get(
        "/api/books",
        headers={"Authorization": "Bearer secret-token-123"},
    )
    assert resp.status_code == 200


def test_health_check_unprotected(protected_client):
    """健康检查 /health 不需要鉴权"""
    resp = protected_client.get("/health")
    assert resp.status_code == 200


def test_root_unprotected(protected_client):
    """根路径 / 不需要鉴权"""
    resp = protected_client.get("/")
    assert resp.status_code == 200


def test_docs_unprotected(protected_client):
    """API 文档不需要鉴权"""
    resp = protected_client.get("/docs")
    # /docs 可能是 200 或重定向
    assert resp.status_code in (200, 307)
