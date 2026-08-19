"""测试基础设施健康检查（不依赖任何业务端点实现状态）。

守护 ``tests/conftest.py`` 提供的测试基础不被破坏：

- ``client`` fixture 可用并指向测试配置；
- 隔离 SQLite 生效，测试不触碰 ``database/library.db``；
- ``route_map`` 能探测到已实现端点（当前为 ``/api/health``）；
- ``make_access_token`` 生成的 JWT 遵循设计文档 §6.2 payload 契约；
- conftest 注入的测试环境变量对 ``get_settings`` 生效。

本模块不断言任何业务端点是否实现，因此后端演进时始终保持稳定。
"""

import os

from jose import jwt

from backend.app.core.config import get_settings


def test_client_fixture_can_request_health(client):
    """client fixture 可请求已实现端点，并采用测试环境配置。"""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["environment"] == "testing"


def test_isolated_database_not_created_on_disk(client):
    """依赖覆盖生效：请求后不会在磁盘产生 database/library.db（§13.2 禁止写入）。"""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert not os.path.exists("database/library.db")


def test_route_map_detects_implemented_endpoint(route_map):
    """route_map 能探测到当前已实现的端点。"""
    assert ("GET", "/api/health") in route_map


def test_make_access_token_payload_contract(make_access_token):
    """生成的 JWT 符合设计文档 §6.2 payload 契约。"""
    token = make_access_token(sub=12, username="librarian")
    payload = jwt.decode(
        token, os.environ["SECRET_KEY"], algorithms=[os.environ["JWT_ALGORITHM"]]
    )
    assert payload["sub"] == "12"
    assert payload["username"] == "librarian"
    assert payload["type"] == "access"
    assert "iat" in payload
    assert "exp" in payload


def test_settings_use_test_environment():
    """conftest 注入的测试环境变量已对 settings 生效。"""
    settings = get_settings()
    assert settings.environment == "testing"
    assert settings.database_url == "sqlite://"
