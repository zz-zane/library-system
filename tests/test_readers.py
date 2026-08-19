"""读者端点契约测试（依据 ``docs/system-design.md`` §8.5 读者、§7 通用契约）。

覆盖：分页/筛选、唯一冲突（phone/email）、联系方式校验、删除保护、停用、
401/404/409/422 边界。端点缺失时由 ``require_routes`` 标记预期失败；
端点已存在时真实执行（不掩盖缺陷）。
"""

READERS_LIST_ROUTE = ("GET", "/api/readers")
READERS_CREATE_ROUTE = ("POST", "/api/readers")
READERS_GET_ROUTE = ("GET", "/api/readers/{reader_id}")
READERS_UPDATE_ROUTE = ("PUT", "/api/readers/{reader_id}")
READERS_DELETE_ROUTE = ("DELETE", "/api/readers/{reader_id}")


def _require_readers(require_routes):
    require_routes(
        {READERS_LIST_ROUTE, READERS_CREATE_ROUTE, READERS_GET_ROUTE,
         READERS_UPDATE_ROUTE, READERS_DELETE_ROUTE},
        "M2 读者端点未实现",
    )


def _reader_payload(phone="13800000001", email="reader@example.com", **extra):
    payload = {"name": "测试读者", "phone": phone, "email": email}
    payload.update(extra)
    return payload


# ---------------------------------------------------------------------------
# 正常路径
# ---------------------------------------------------------------------------


def test_list_readers_returns_page(client, admin_headers, db_session, make_reader, require_routes):
    """GET /api/readers → 200 Page[ReaderOut] 结构（§7.2）。"""
    _require_readers(require_routes)
    make_reader(name="读者甲", phone="13800000001")

    resp = client.get("/api/readers", headers=admin_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert {"items", "total", "page", "page_size", "pages"} <= set(data)
    assert data["total"] == 1
    assert data["items"][0]["name"] == "读者甲"
    assert data["items"][0]["status"] == "active"


def test_create_reader_returns_201(client, admin_headers, require_routes):
    """POST /api/readers → 201 ReaderOut，默认 status=active（§8.5）。"""
    _require_readers(require_routes)

    resp = client.post(
        "/api/readers", headers=admin_headers,
        json=_reader_payload(name="新读者", email="new@example.com"),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "新读者"
    assert data["status"] == "active"
    assert data["email"] == "new@example.com"


def test_get_reader_returns_200(client, admin_headers, db_session, make_reader, require_routes):
    _require_readers(require_routes)
    reader = make_reader(name="获取读者", phone="13800000002")

    resp = client.get(f"/api/readers/{reader.id}", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["id"] == reader.id


def test_update_reader_returns_200(client, admin_headers, db_session, make_reader, require_routes):
    _require_readers(require_routes)
    reader = make_reader(name="改名", phone="13800000001")

    resp = client.put(f"/api/readers/{reader.id}", headers=admin_headers, json={"name": "新名字"})

    assert resp.status_code == 200
    assert resp.json()["name"] == "新名字"


def test_delete_reader_without_history_204(client, admin_headers, db_session, make_reader, require_routes):
    """无借阅历史的读者可删除 → 204（§8.5、D-15）。"""
    _require_readers(require_routes)
    reader = make_reader(name="待删除", phone="13800000001")

    resp = client.delete(f"/api/readers/{reader.id}", headers=admin_headers)

    assert resp.status_code == 204
    assert client.get(f"/api/readers/{reader.id}", headers=admin_headers).status_code == 404


# ---------------------------------------------------------------------------
# 分页与筛选
# ---------------------------------------------------------------------------


def test_list_readers_filter_by_keyword(client, admin_headers, db_session, make_reader, require_routes):
    """keyword 同时匹配 name/phone/email（§8.5）。"""
    _require_readers(require_routes)
    make_reader(name="张三", phone="13800000001", email="zhang@example.com")
    make_reader(name="李四", phone="13900000002", email="li@example.com")

    by_name = client.get("/api/readers", headers=admin_headers, params={"keyword": "张三"})
    assert by_name.json()["total"] == 1
    assert by_name.json()["items"][0]["name"] == "张三"

    by_phone = client.get("/api/readers", headers=admin_headers, params={"keyword": "13900000002"})
    assert by_phone.json()["total"] == 1
    assert by_phone.json()["items"][0]["name"] == "李四"

    by_email = client.get("/api/readers", headers=admin_headers, params={"keyword": "zhang@example.com"})
    assert by_email.json()["total"] == 1


def test_list_readers_filter_by_status(client, admin_headers, db_session, make_reader, require_routes):
    _require_readers(require_routes)
    make_reader(name="启用读者", phone="13800000001", status="active")
    make_reader(name="停用读者", phone="13900000002", status="disabled")

    resp = client.get("/api/readers", headers=admin_headers, params={"status": "disabled"})

    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["name"] == "停用读者"


def test_list_readers_page_bounds_422(client, admin_headers, require_routes):
    """分页边界：page=0、page_size=0/101 → 422（§7.2）。"""
    _require_readers(require_routes)

    assert client.get("/api/readers", headers=admin_headers, params={"page": 0}).status_code == 422
    assert client.get("/api/readers", headers=admin_headers, params={"page_size": 0}).status_code == 422
    assert client.get("/api/readers", headers=admin_headers, params={"page_size": 101}).status_code == 422


# ---------------------------------------------------------------------------
# 401 / 404
# ---------------------------------------------------------------------------


def test_list_readers_without_token_401(client, require_routes):
    _require_readers(require_routes)

    assert client.get("/api/readers").status_code == 401


def test_create_reader_without_token_401(client, require_routes):
    _require_readers(require_routes)

    resp = client.post("/api/readers", json=_reader_payload())

    assert resp.status_code == 401


def test_get_reader_not_found_404(client, admin_headers, require_routes):
    _require_readers(require_routes)

    assert client.get("/api/readers/999999", headers=admin_headers).status_code == 404


def test_update_reader_not_found_404(client, admin_headers, require_routes):
    _require_readers(require_routes)

    resp = client.put("/api/readers/999999", headers=admin_headers, json={"name": "改名"})

    assert resp.status_code == 404


def test_delete_reader_not_found_404(client, admin_headers, require_routes):
    _require_readers(require_routes)

    assert client.delete("/api/readers/999999", headers=admin_headers).status_code == 404


# ---------------------------------------------------------------------------
# 409 唯一冲突 / 业务冲突
# ---------------------------------------------------------------------------


def test_create_reader_duplicate_phone_409(client, admin_headers, db_session, make_reader, require_routes):
    """重复 phone → 409（§8.5）。"""
    _require_readers(require_routes)
    make_reader(name="已存在", phone="13800000001", email="a@example.com")

    resp = client.post(
        "/api/readers", headers=admin_headers,
        json=_reader_payload(phone="13800000001", email="b@example.com", name="重复"),
    )

    assert resp.status_code == 409


def test_create_reader_duplicate_email_409(client, admin_headers, db_session, make_reader, require_routes):
    """重复 email → 409（§8.5）。"""
    _require_readers(require_routes)
    make_reader(name="已存在", phone="13800000001", email="dup@example.com")

    resp = client.post(
        "/api/readers", headers=admin_headers,
        json=_reader_payload(phone="13900000002", email="dup@example.com", name="重复"),
    )

    assert resp.status_code == 409


def test_delete_reader_with_history_409(client, admin_headers, db_session, make_reader,
                                       make_book, make_user, make_borrow, require_routes):
    """存在借阅历史的读者禁止删除 → 409（§8.5、D-15）。"""
    _require_readers(require_routes)
    reader = make_reader(name="有历史", phone="13800000001")
    book = make_book(title="图书", total_copies=2)
    user = make_user(username="librarian", password="password123")
    make_borrow(book_id=book.id, reader_id=reader.id, borrowed_by=user.id)

    resp = client.delete(f"/api/readers/{reader.id}", headers=admin_headers)

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 422 校验边界
# ---------------------------------------------------------------------------


def test_create_reader_missing_contact_422(client, admin_headers, require_routes):
    """phone 与 email 至少填写一项；全空 → 422（§5.3、§8.5）。"""
    _require_readers(require_routes)

    resp = client.post("/api/readers", headers=admin_headers, json={"name": "无联系方式"})

    assert resp.status_code == 422


def test_create_reader_invalid_email_422(client, admin_headers, require_routes):
    """email 格式非法 → 422（§5.3 Pydantic 邮箱校验）。"""
    _require_readers(require_routes)

    resp = client.post(
        "/api/readers", headers=admin_headers,
        json={"name": "非法邮箱", "phone": "13800000001", "email": "not-an-email"},
    )

    assert resp.status_code == 422


def test_create_reader_unknown_field_422(client, admin_headers, require_routes):
    """未知请求字段 → 422（§7.1）。"""
    _require_readers(require_routes)

    resp = client.post(
        "/api/readers", headers=admin_headers,
        json=_reader_payload(role="vip"),
    )

    assert resp.status_code == 422


def test_update_reader_empty_body_422(client, admin_headers, db_session, make_reader, require_routes):
    """ReaderUpdate 至少提供一项；空更新 → 422（§8.5）。"""
    _require_readers(require_routes)
    reader = make_reader(name="空更新", phone="13800000001")

    resp = client.put(f"/api/readers/{reader.id}", headers=admin_headers, json={})

    assert resp.status_code == 422


def test_update_reader_invalid_status_422(client, admin_headers, db_session, make_reader, require_routes):
    """status 只允许 active/disabled（§8.5）。"""
    _require_readers(require_routes)
    reader = make_reader(name="状态测试", phone="13800000001")

    resp = client.put(f"/api/readers/{reader.id}", headers=admin_headers, json={"status": "suspended"})

    assert resp.status_code == 422


def test_update_reader_missing_contact_422(client, admin_headers, db_session, make_reader, require_routes):
    """更新后 phone/email 全空 → 422（§8.5）。"""
    _require_readers(require_routes)
    reader = make_reader(name="联系方式", phone="13800000001", email=None)

    resp = client.put(
        f"/api/readers/{reader.id}", headers=admin_headers,
        json={"phone": ""},
    )

    assert resp.status_code == 422
