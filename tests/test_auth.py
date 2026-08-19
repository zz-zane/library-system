"""认证端点契约测试（依据 ``docs/system-design.md`` §6 认证与授权、§8.2 认证）。

当前基线处于 M0 脚手架阶段，认证端点（``/api/auth/*``）尚未实现。
本模块以设计契约驱动编写测试，覆盖正常、401、422 边界；端点缺失时由
``require_routes`` 标记为预期失败（xfail）。后端 M2 实现后，这些测试自动
转为真实执行，无需改动。

设计依据：
- §8.2 ``POST /api/auth/login``：200 ``TokenOut``；凭据无效/账号停用 401；字段缺失或格式错误 422。
- §8.2 ``GET /api/auth/me``：Bearer 认证；200 ``UserOut``；token 或用户无效 401。
- §6.2 JWT 契约：token 缺失/格式错误/签名错误/过期/用户不存在或停用，统一 401 + ``WWW-Authenticate: Bearer``。
- §6.3 登录失败统一返回 ``{"detail": "用户名或密码错误"}``，不暴露用户名是否存在或账号是否停用。
"""

from datetime import timedelta

AUTH_LOGIN_ROUTE = ("POST", "/api/auth/login")
AUTH_ME_ROUTE = ("GET", "/api/auth/me")

VALID_LOGIN = {"username": "librarian", "password": "password123"}


# ---------------------------------------------------------------------------
# POST /api/auth/login —— 正常路径
# ---------------------------------------------------------------------------


def test_login_success_returns_bearer_token(client, db_session, make_user, require_routes):
    """有效凭据 → 200 ``TokenOut``（access_token + token_type=bearer）。"""
    require_routes({AUTH_LOGIN_ROUTE}, "M2 认证端点未实现：POST /api/auth/login 契约测试预期失败")
    make_user(username="librarian", password="password123", display_name="管理员")

    resp = client.post("/api/auth/login", json=VALID_LOGIN)

    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


# ---------------------------------------------------------------------------
# POST /api/auth/login —— 401 边界
# ---------------------------------------------------------------------------


def test_login_wrong_password_401(client, db_session, make_user, require_routes):
    """密码错误 → 401。"""
    require_routes({AUTH_LOGIN_ROUTE}, "M2 认证端点未实现：POST /api/auth/login 契约测试预期失败")
    make_user(username="librarian", password="password123")

    resp = client.post(
        "/api/auth/login", json={"username": "librarian", "password": "wrong-password"}
    )

    assert resp.status_code == 401


def test_login_unknown_username_401(client, require_routes):
    """用户名不存在 → 401，且不暴露用户名是否存在（§6.3 统一信息）。"""
    require_routes({AUTH_LOGIN_ROUTE}, "M2 认证端点未实现：POST /api/auth/login 契约测试预期失败")

    resp = client.post(
        "/api/auth/login", json={"username": "nobody", "password": "password123"}
    )

    assert resp.status_code == 401


def test_login_inactive_user_401(client, db_session, make_user, require_routes):
    """停用账号不能登录，与普通失败返回一致（§6.4 权限矩阵）。"""
    require_routes({AUTH_LOGIN_ROUTE}, "M2 认证端点未实现：POST /api/auth/login 契约测试预期失败")
    make_user(username="disabled_user", password="password123", is_active=False)

    resp = client.post(
        "/api/auth/login", json={"username": "disabled_user", "password": "password123"}
    )

    assert resp.status_code == 401


def test_login_failure_detail_is_uniform(client, db_session, make_user, require_routes):
    """错密码与未知用户名返回完全相同的 401 detail（§6.3）。"""
    require_routes({AUTH_LOGIN_ROUTE}, "M2 认证端点未实现：POST /api/auth/login 契约测试预期失败")
    make_user(username="librarian", password="password123")

    wrong_pw = client.post(
        "/api/auth/login", json={"username": "librarian", "password": "wrong-password"}
    )
    unknown = client.post(
        "/api/auth/login", json={"username": "nobody", "password": "password123"}
    )

    assert wrong_pw.status_code == 401
    assert unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()
    assert wrong_pw.json().get("detail")


# ---------------------------------------------------------------------------
# POST /api/auth/login —— 422 边界
# ---------------------------------------------------------------------------


def test_login_missing_username_422(client, require_routes):
    """请求体缺少 username → 422。"""
    require_routes({AUTH_LOGIN_ROUTE}, "M2 认证端点未实现：POST /api/auth/login 契约测试预期失败")

    resp = client.post("/api/auth/login", json={"password": "password123"})

    assert resp.status_code == 422


def test_login_missing_password_422(client, require_routes):
    """请求体缺少 password → 422。"""
    require_routes({AUTH_LOGIN_ROUTE}, "M2 认证端点未实现：POST /api/auth/login 契约测试预期失败")

    resp = client.post("/api/auth/login", json={"username": "librarian"})

    assert resp.status_code == 422


def test_login_empty_body_422(client, require_routes):
    """空请求体 → 422。"""
    require_routes({AUTH_LOGIN_ROUTE}, "M2 认证端点未实现：POST /api/auth/login 契约测试预期失败")

    resp = client.post("/api/auth/login", json={})

    assert resp.status_code == 422


def test_login_unknown_field_422(client, require_routes):
    """未知请求字段由 Pydantic schema 拒绝 → 422（§7.1、§7.3）。"""
    require_routes({AUTH_LOGIN_ROUTE}, "M2 认证端点未实现：POST /api/auth/login 契约测试预期失败")

    resp = client.post("/api/auth/login", json={**VALID_LOGIN, "remember_me": True})

    assert resp.status_code == 422


def test_login_non_string_username_422(client, require_routes):
    """username 类型非字符串 → 422。"""
    require_routes({AUTH_LOGIN_ROUTE}, "M2 认证端点未实现：POST /api/auth/login 契约测试预期失败")

    resp = client.post("/api/auth/login", json={"username": 123, "password": "password123"})

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/auth/me —— 正常路径
# ---------------------------------------------------------------------------


def test_me_returns_current_user(client, require_routes, make_access_token, bearer_headers):
    """有效 Bearer token → 200 ``UserOut``（id/username/display_name/is_active，§8.3）。"""
    require_routes({AUTH_ME_ROUTE}, "M2 认证端点未实现：GET /api/auth/me 契约测试预期失败")

    token = make_access_token(sub=1, username="librarian")
    resp = client.get("/api/auth/me", headers=bearer_headers(token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["username"] == "librarian"
    assert "display_name" in data
    assert "is_active" in data


# ---------------------------------------------------------------------------
# GET /api/auth/me —— 401 边界
# ---------------------------------------------------------------------------


def test_me_without_token_401(client, require_routes):
    """缺少 Authorization 头 → 401，并附带 ``WWW-Authenticate: Bearer``（§6.2）。"""
    require_routes({AUTH_ME_ROUTE}, "M2 认证端点未实现：GET /api/auth/me 契约测试预期失败")

    resp = client.get("/api/auth/me")

    assert resp.status_code == 401
    assert resp.headers.get("www-authenticate") == "Bearer"


def test_me_malformed_token_401(client, require_routes, bearer_headers):
    """token 格式损坏 → 401（§6.2）。"""
    require_routes({AUTH_ME_ROUTE}, "M2 认证端点未实现：GET /api/auth/me 契约测试预期失败")

    resp = client.get("/api/auth/me", headers=bearer_headers("not-a-valid-jwt"))

    assert resp.status_code == 401


def test_me_expired_token_401(client, require_routes, make_access_token, bearer_headers):
    """已过期 token → 401（§6.2）。"""
    require_routes({AUTH_ME_ROUTE}, "M2 认证端点未实现：GET /api/auth/me 契约测试预期失败")

    token = make_access_token(sub=1, username="librarian", expires_delta=timedelta(minutes=-5))
    resp = client.get("/api/auth/me", headers=bearer_headers(token))

    assert resp.status_code == 401


def test_me_wrong_signature_token_401(client, require_routes, make_access_token, bearer_headers):
    """签名错误（使用其他密钥签发）→ 401（§6.2）。"""
    require_routes({AUTH_ME_ROUTE}, "M2 认证端点未实现：GET /api/auth/me 契约测试预期失败")

    token = make_access_token(sub=1, username="librarian", secret_key="a-different-secret")
    resp = client.get("/api/auth/me", headers=bearer_headers(token))

    assert resp.status_code == 401


def test_me_unknown_user_token_401(client, require_routes, make_access_token, bearer_headers):
    """签名有效但 ``sub`` 指向不存在的用户 → 401（§6.2 每次鉴权查库）。"""
    require_routes({AUTH_ME_ROUTE}, "M2 认证端点未实现：GET /api/auth/me 契约测试预期失败")

    token = make_access_token(sub=999999, username="ghost")
    resp = client.get("/api/auth/me", headers=bearer_headers(token))

    assert resp.status_code == 401


def test_me_inactive_user_token_401(client, db_session, make_user, require_routes,
                                    make_access_token, bearer_headers):
    """停用账号即使持有有效 token 也返回 401（§6.4、§5.2 停用即生效）。"""
    require_routes({AUTH_ME_ROUTE}, "M2 认证端点未实现：GET /api/auth/me 契约测试预期失败")

    user = make_user(username="disabled_user", password="password123", is_active=False)
    token = make_access_token(sub=user.id, username="disabled_user")
    resp = client.get("/api/auth/me", headers=bearer_headers(token))

    assert resp.status_code == 401
