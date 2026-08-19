"""操作员端点契约测试（依据 ``docs/system-design.md`` §8.3 操作员、§7 通用契约）。

当前基线处于 M0 脚手架阶段，操作员端点（``/api/users``）尚未实现。
本模块以设计契约驱动编写测试，覆盖正常、401、409、404、422 边界；
端点缺失时由 ``require_routes`` 标记为预期失败（xfail）。后端 M2 实现后，
这些测试自动转为真实执行，无需改动。

设计依据：
- §8.3 ``GET /api/users`` → 200 ``Page[UserOut]``；``POST /api/users`` → 201 ``UserOut``；
  ``PUT /api/users/{user_id}`` → 200 ``UserOut``。
- §7.2 分页：``page ≥ 1``、``page_size 1–100``、默认 ``page=1 page_size=20``、默认排序 ``id desc``。
- §5.2 约束：用户名 ``^[A-Za-z0-9_]{3,64}$``；不允许自停用；不允许停用最后一个启用操作员。
- D-05 密码至少 8 字符；密码与 ``password_hash`` 不得出现在任何输出模型（§8.3）。
- §7.1 未知请求字段由 Pydantic schema 拒绝 → 422。
"""

USERS_LIST_ROUTE = ("GET", "/api/users")
USERS_CREATE_ROUTE = ("POST", "/api/users")
USERS_UPDATE_ROUTE = ("PUT", "/api/users/{user_id}")


def _require_users(require_routes):
    require_routes(
        {USERS_LIST_ROUTE, USERS_CREATE_ROUTE, USERS_UPDATE_ROUTE},
        "M2 操作员端点未实现：/api/users 契约测试预期失败",
    )


# ---------------------------------------------------------------------------
# GET /api/users —— 正常路径
# ---------------------------------------------------------------------------


def test_list_users_returns_page(client, require_routes, admin_headers):
    """已认证请求 → 200 ``Page[UserOut]`` 结构（§7.2）。"""
    _require_users(require_routes)

    resp = client.get("/api/users", headers=admin_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert {"items", "total", "page", "page_size", "pages"} <= set(data)
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_list_users_defaults_to_id_desc(client, require_routes, admin_headers, db_session, make_user):
    """默认排序 ``id desc``；每项为 ``UserOut`` 且不含密码字段（§7.2、§8.3）。"""
    _require_users(require_routes)
    make_user(username="user_a", password="password123")
    make_user(username="user_b", password="password123")

    resp = client.get("/api/users", headers=admin_headers)

    assert resp.status_code == 200
    data = resp.json()
    # admin + user_a + user_b
    assert data["total"] == 3
    ids = [u["id"] for u in data["items"]]
    assert ids == sorted(ids, reverse=True)
    for item in data["items"]:
        assert {"id", "username", "display_name", "is_active", "created_at", "updated_at"} <= set(item)
        assert "password" not in item
        assert "password_hash" not in item


# ---------------------------------------------------------------------------
# POST /api/users —— 正常路径
# ---------------------------------------------------------------------------


def test_create_user_returns_201(client, require_routes, admin_headers):
    """有效 ``UserCreate`` → 201 ``UserOut``，密码不回显（§8.3、§6.3）。"""
    _require_users(require_routes)

    resp = client.post(
        "/api/users",
        headers=admin_headers,
        json={"username": "new_operator", "password": "password123", "display_name": "新操作员"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "new_operator"
    assert data["display_name"] == "新操作员"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


# ---------------------------------------------------------------------------
# PUT /api/users/{user_id} —— 正常路径
# ---------------------------------------------------------------------------


def test_update_user_returns_200(client, require_routes, admin_headers, db_session, make_user):
    """有效 ``UserUpdate`` → 200 ``UserOut``（§8.3）。"""
    _require_users(require_routes)
    target = make_user(username="target_op", password="password123")

    resp = client.put(
        f"/api/users/{target.id}", headers=admin_headers, json={"display_name": "改名后"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "改名后"
    assert "password" not in data
    assert "password_hash" not in data


# ---------------------------------------------------------------------------
# 401 边界（未认证请求）
# ---------------------------------------------------------------------------


def test_list_users_without_token_401(client, require_routes):
    _require_users(require_routes)

    resp = client.get("/api/users")

    assert resp.status_code == 401


def test_create_user_without_token_401(client, require_routes):
    _require_users(require_routes)

    resp = client.post(
        "/api/users", json={"username": "nobody", "password": "password123"}
    )

    assert resp.status_code == 401


def test_update_user_without_token_401(client, require_routes):
    _require_users(require_routes)

    resp = client.put("/api/users/1", json={"display_name": "x"})

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 409 边界（唯一/状态冲突）
# ---------------------------------------------------------------------------


def test_create_user_duplicate_username_409(client, require_routes, admin_headers, db_session, make_user):
    """重复用户名 → 409（§8.3）。"""
    _require_users(require_routes)
    make_user(username="dup_user", password="password123")

    resp = client.post(
        "/api/users",
        headers=admin_headers,
        json={"username": "dup_user", "password": "password123"},
    )

    assert resp.status_code == 409


def test_update_user_self_deactivate_409(client, require_routes, admin_headers, db_session, make_user):
    """不允许停用当前登录账号，即使系统中还有其他启用账号（§5.2）。"""
    _require_users(require_routes)
    make_user(username="another_op", password="password123")

    resp = client.get("/api/users", headers=admin_headers)
    admin_id = next(u["id"] for u in resp.json()["items"] if u["username"] == "admin")

    resp2 = client.put(f"/api/users/{admin_id}", headers=admin_headers, json={"is_active": False})

    assert resp2.status_code == 409


def test_update_user_last_active_deactivate_409(client, require_routes, admin_headers,
                                                db_session, make_user):
    """不允许停用最后一个启用的操作员，避免系统失去可登录账号（§5.2）。"""
    _require_users(require_routes)
    # 存在一个停用账号，但启用的只有 admin
    make_user(username="disabled_op", password="password123", is_active=False)

    resp = client.get("/api/users", headers=admin_headers)
    admin_id = next(u["id"] for u in resp.json()["items"] if u["username"] == "admin")

    resp2 = client.put(f"/api/users/{admin_id}", headers=admin_headers, json={"is_active": False})

    assert resp2.status_code == 409


# ---------------------------------------------------------------------------
# 404 边界
# ---------------------------------------------------------------------------


def test_update_user_not_found_404(client, require_routes, admin_headers):
    """不存在的 user_id → 404（§7.3）。"""
    _require_users(require_routes)

    resp = client.put("/api/users/999999", headers=admin_headers, json={"display_name": "x"})

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 422 边界（Pydantic 校验）
# ---------------------------------------------------------------------------


def test_create_user_username_too_short_422(client, require_routes, admin_headers):
    """用户名少于 3 字符 → 422（§5.2 ``^[A-Za-z0-9_]{3,64}$``）。"""
    _require_users(require_routes)

    resp = client.post(
        "/api/users", headers=admin_headers, json={"username": "ab", "password": "password123"}
    )

    assert resp.status_code == 422


def test_create_user_username_invalid_chars_422(client, require_routes, admin_headers):
    """用户名含非法字符（如空格）→ 422（§5.2）。"""
    _require_users(require_routes)

    resp = client.post(
        "/api/users", headers=admin_headers, json={"username": "has space", "password": "password123"}
    )

    assert resp.status_code == 422


def test_create_user_username_too_long_422(client, require_routes, admin_headers):
    """用户名超过 64 字符 → 422（§5.2）。"""
    _require_users(require_routes)

    resp = client.post(
        "/api/users", headers=admin_headers, json={"username": "a" * 65, "password": "password123"}
    )

    assert resp.status_code == 422


def test_create_user_password_too_short_422(client, require_routes, admin_headers):
    """明文密码少于 8 字符 → 422（D-05、§6.3）。"""
    _require_users(require_routes)

    resp = client.post(
        "/api/users", headers=admin_headers, json={"username": "op_user", "password": "short"}
    )

    assert resp.status_code == 422


def test_create_user_password_too_long_422(client, require_routes, admin_headers):
    """明文密码超过 128 字符 → 422（§6.3）。"""
    _require_users(require_routes)

    resp = client.post(
        "/api/users", headers=admin_headers, json={"username": "op_user", "password": "p" * 129}
    )

    assert resp.status_code == 422


def test_create_user_unknown_field_422(client, require_routes, admin_headers):
    """未知请求字段由 Pydantic schema 拒绝 → 422（§7.1）。"""
    _require_users(require_routes)

    resp = client.post(
        "/api/users",
        headers=admin_headers,
        json={"username": "op_user", "password": "password123", "role": "admin"},
    )

    assert resp.status_code == 422


def test_update_user_empty_body_422(client, require_routes, admin_headers, db_session, make_user):
    """``UserUpdate`` 至少提供一项；空更新 → 422（§8.3）。"""
    _require_users(require_routes)
    target = make_user(username="target_op", password="password123")

    resp = client.put(f"/api/users/{target.id}", headers=admin_headers, json={})

    assert resp.status_code == 422


def test_list_users_page_zero_422(client, require_routes, admin_headers):
    """``page=0`` → 422（§7.2 page 从 1 开始）。"""
    _require_users(require_routes)

    resp = client.get("/api/users", headers=admin_headers, params={"page": 0})

    assert resp.status_code == 422


def test_list_users_page_size_zero_422(client, require_routes, admin_headers):
    """``page_size=0`` → 422（§7.2 page_size 1–100）。"""
    _require_users(require_routes)

    resp = client.get("/api/users", headers=admin_headers, params={"page_size": 0})

    assert resp.status_code == 422


def test_list_users_page_size_over_max_422(client, require_routes, admin_headers):
    """``page_size=101`` 超过上限 → 422（§7.2 page_size 上限 100）。"""
    _require_users(require_routes)

    resp = client.get("/api/users", headers=admin_headers, params={"page_size": 101})

    assert resp.status_code == 422
