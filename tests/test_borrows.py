"""借阅端点契约测试（依据 ``docs/system-design.md`` §8.6 借阅、§9 借阅业务规则）。

覆盖：借出/归还库存原子变化、库存不足、读者停用、最大 5 本、逾期禁借、
重复归还、非法 due_date、筛选、401/404/409/422 边界。
端点缺失时由 ``require_routes`` 标记预期失败；端点已存在时真实执行（不掩盖缺陷）。
"""

from datetime import date, timedelta

BORROWS_LIST_ROUTE = ("GET", "/api/borrows")
BORROWS_CREATE_ROUTE = ("POST", "/api/borrows")
BORROWS_GET_ROUTE = ("GET", "/api/borrows/{borrow_id}")
BORROWS_RETURN_ROUTE = ("POST", "/api/borrows/{borrow_id}/return")


def _require_borrows(require_routes):
    require_routes(
        {BORROWS_LIST_ROUTE, BORROWS_CREATE_ROUTE, BORROWS_GET_ROUTE, BORROWS_RETURN_ROUTE},
        "M2 借阅端点未实现",
    )


def _available(client, book_id, headers):
    return client.get(f"/api/books/{book_id}", headers=headers).json()["available_copies"]


# ---------------------------------------------------------------------------
# 借出 / 归还 库存原子变化
# ---------------------------------------------------------------------------


def test_create_borrow_decreases_inventory(client, admin_headers, db_session,
                                           make_book, make_reader, require_routes):
    """借出成功 → 201，可用库存 -1（§9.2 条件原子更新）。"""
    _require_borrows(require_routes)
    book = make_book(title="库存书", total_copies=2)
    reader = make_reader(name="读者甲", phone="13800000001")

    resp = client.post(
        "/api/borrows", headers=admin_headers,
        json={"book_id": book.id, "reader_id": reader.id},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "borrowed"
    assert data["book"]["id"] == book.id
    assert data["reader"]["id"] == reader.id
    assert data["borrowed_by"]["username"] == "admin"
    assert data["returned_at"] is None
    assert _available(client, book.id, admin_headers) == 1


def test_return_borrow_increases_inventory(client, admin_headers, db_session,
                                           make_book, make_reader, require_routes):
    """归还成功 → 200，状态 returned，可用库存 +1（§9.3）。"""
    _require_borrows(require_routes)
    book = make_book(title="归还书", total_copies=2)
    reader = make_reader(name="读者甲", phone="13800000001")
    borrow_id = client.post(
        "/api/borrows", headers=admin_headers,
        json={"book_id": book.id, "reader_id": reader.id},
    ).json()["id"]
    assert _available(client, book.id, admin_headers) == 1

    resp = client.post(f"/api/borrows/{borrow_id}/return", headers=admin_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "returned"
    assert data["returned_by"]["username"] == "admin"
    assert data["returned_at"] is not None
    assert _available(client, book.id, admin_headers) == 2


# ---------------------------------------------------------------------------
# 正常路径：详情 / 列表
# ---------------------------------------------------------------------------


def test_get_borrow_returns_200(client, admin_headers, db_session,
                                make_book, make_reader, require_routes):
    _require_borrows(require_routes)
    book = make_book(title="详情书", total_copies=2)
    reader = make_reader(name="读者甲", phone="13800000001")
    borrow_id = client.post(
        "/api/borrows", headers=admin_headers,
        json={"book_id": book.id, "reader_id": reader.id},
    ).json()["id"]

    resp = client.get(f"/api/borrows/{borrow_id}", headers=admin_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == borrow_id
    assert data["status"] == "borrowed"


def test_list_borrows_returns_page(client, admin_headers, db_session,
                                   make_book, make_reader, require_routes):
    _require_borrows(require_routes)
    book = make_book(title="列表书", total_copies=2)
    reader = make_reader(name="读者甲", phone="13800000001")
    client.post("/api/borrows", headers=admin_headers,
                json={"book_id": book.id, "reader_id": reader.id})

    resp = client.get("/api/borrows", headers=admin_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert {"items", "total", "page", "page_size", "pages"} <= set(data)
    assert data["total"] == 1
    assert data["items"][0]["status"] == "borrowed"


# ---------------------------------------------------------------------------
# 业务规则：库存不足 / 读者停用 / 上限 / 逾期 / 重复归还 / 非法 due_date
# ---------------------------------------------------------------------------


def test_borrow_insufficient_inventory_409(client, admin_headers, db_session,
                                           make_book, make_reader, require_routes):
    """可用库存为 0 时借出 → 409（§9.2 条件原子更新失败）。"""
    _require_borrows(require_routes)
    book = make_book(title="单库存", total_copies=1)
    reader = make_reader(name="读者甲", phone="13800000001")

    r1 = client.post("/api/borrows", headers=admin_headers,
                     json={"book_id": book.id, "reader_id": reader.id})
    assert r1.status_code == 201
    r2 = client.post("/api/borrows", headers=admin_headers,
                     json={"book_id": book.id, "reader_id": reader.id})

    assert r2.status_code == 409


def test_borrow_reader_disabled_409(client, admin_headers, db_session,
                                    make_book, make_reader, require_routes):
    """停用读者禁止创建新借阅 → 409（§5.3、§9.2）。"""
    _require_borrows(require_routes)
    book = make_book(title="图书", total_copies=2)
    reader = make_reader(name="停用读者", phone="13800000001")
    assert client.put(
        f"/api/readers/{reader.id}", headers=admin_headers, json={"status": "disabled"}
    ).status_code == 200

    resp = client.post("/api/borrows", headers=admin_headers,
                       json={"book_id": book.id, "reader_id": reader.id})

    assert resp.status_code == 409


def test_borrow_exceeds_max_concurrent_409(client, admin_headers, db_session,
                                           make_book, make_reader, require_routes):
    """同时未归还超过上限（默认 5）→ 409（D-12、§9.2）。"""
    _require_borrows(require_routes)
    reader = make_reader(name="读者甲", phone="13800000001")
    books = [make_book(title=f"上限书{i}", total_copies=1) for i in range(6)]

    for book in books[:5]:
        r = client.post("/api/borrows", headers=admin_headers,
                        json={"book_id": book.id, "reader_id": reader.id})
        assert r.status_code == 201

    resp = client.post("/api/borrows", headers=admin_headers,
                       json={"book_id": books[5].id, "reader_id": reader.id})

    assert resp.status_code == 409


def test_borrow_reader_overdue_409(client, admin_headers, db_session,
                                   make_book, make_reader, make_user, make_borrow,
                                   require_routes):
    """读者存在逾期未还记录时禁止继续借阅 → 409（D-12、§9.2）。"""
    _require_borrows(require_routes)
    reader = make_reader(name="逾期读者", phone="13800000001")
    old_book = make_book(title="旧书", total_copies=2)
    user = make_user(username="librarian", password="password123")
    make_borrow(book_id=old_book.id, reader_id=reader.id, borrowed_by=user.id,
                due_date=date.today() - timedelta(days=3))

    new_book = make_book(title="新书", total_copies=2)
    resp = client.post("/api/borrows", headers=admin_headers,
                       json={"book_id": new_book.id, "reader_id": reader.id})

    assert resp.status_code == 409


def test_return_already_returned_409(client, admin_headers, db_session,
                                     make_book, make_reader, require_routes):
    """重复归还 → 409，且不重复增加库存（§9.3）。"""
    _require_borrows(require_routes)
    book = make_book(title="重复归还", total_copies=2)
    reader = make_reader(name="读者甲", phone="13800000001")
    borrow_id = client.post(
        "/api/borrows", headers=admin_headers,
        json={"book_id": book.id, "reader_id": reader.id},
    ).json()["id"]
    assert client.post(f"/api/borrows/{borrow_id}/return", headers=admin_headers).status_code == 200

    resp = client.post(f"/api/borrows/{borrow_id}/return", headers=admin_headers)

    assert resp.status_code == 409
    assert _available(client, book.id, admin_headers) == 2


def test_borrow_due_date_before_today_422(client, admin_headers, db_session,
                                          make_book, make_reader, require_routes):
    """due_date 早于当前日期 → 422（D-11、§9.2）。"""
    _require_borrows(require_routes)
    book = make_book(title="日期书", total_copies=2)
    reader = make_reader(name="读者甲", phone="13800000001")

    resp = client.post(
        "/api/borrows", headers=admin_headers,
        json={"book_id": book.id, "reader_id": reader.id, "due_date": "2000-01-01"},
    )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 筛选
# ---------------------------------------------------------------------------


def test_list_borrows_filter_by_status(client, admin_headers, db_session,
                                       make_book, make_reader, require_routes):
    """status 筛选：returned 与 borrowed 互斥正确（§8.6）。"""
    _require_borrows(require_routes)
    book = make_book(title="筛选书", total_copies=5)
    reader = make_reader(name="读者甲", phone="13800000001")
    r1 = client.post("/api/borrows", headers=admin_headers,
                     json={"book_id": book.id, "reader_id": reader.id})
    r2 = client.post("/api/borrows", headers=admin_headers,
                     json={"book_id": book.id, "reader_id": reader.id})
    assert client.post(f"/api/borrows/{r1.json()['id']}/return", headers=admin_headers).status_code == 200
    assert r2.status_code == 201

    returned = client.get("/api/borrows", headers=admin_headers, params={"status": "returned"})
    borrowed = client.get("/api/borrows", headers=admin_headers, params={"status": "borrowed"})

    assert returned.status_code == 200
    assert returned.json()["total"] == 1
    assert borrowed.status_code == 200
    assert borrowed.json()["total"] == 1


def test_list_borrows_filter_by_due_before(client, admin_headers, db_session,
                                           make_book, make_reader, require_routes):
    """due_before 筛选到期日不晚于指定日期的记录（§8.6）。"""
    _require_borrows(require_routes)
    book = make_book(title="到期筛选", total_copies=5)
    reader = make_reader(name="读者甲", phone="13800000001")
    r1 = client.post(
        "/api/borrows", headers=admin_headers,
        json={"book_id": book.id, "reader_id": reader.id,
              "due_date": str(date.today())},
    )
    r2 = client.post("/api/borrows", headers=admin_headers,
                     json={"book_id": book.id, "reader_id": reader.id})
    assert r1.status_code == 201
    assert r2.status_code == 201

    resp = client.get("/api/borrows", headers=admin_headers,
                      params={"due_before": str(date.today())})

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_list_borrows_filter_by_book(client, admin_headers, db_session,
                                     make_book, make_reader, require_routes):
    """book_id 筛选（§8.6）。"""
    _require_borrows(require_routes)
    reader = make_reader(name="读者甲", phone="13800000001")
    book_a = make_book(title="书A", total_copies=2)
    book_b = make_book(title="书B", total_copies=2)
    client.post("/api/borrows", headers=admin_headers,
                json={"book_id": book_a.id, "reader_id": reader.id})
    client.post("/api/borrows", headers=admin_headers,
                json={"book_id": book_b.id, "reader_id": reader.id})

    resp = client.get("/api/borrows", headers=admin_headers, params={"book_id": book_a.id})

    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["book"]["id"] == book_a.id


# ---------------------------------------------------------------------------
# 401 / 404
# ---------------------------------------------------------------------------


def test_list_borrows_without_token_401(client, require_routes):
    _require_borrows(require_routes)

    assert client.get("/api/borrows").status_code == 401


def test_create_borrow_without_token_401(client, require_routes):
    _require_borrows(require_routes)

    resp = client.post("/api/borrows", json={"book_id": 1, "reader_id": 1})

    assert resp.status_code == 401


def test_return_borrow_without_token_401(client, require_routes):
    _require_borrows(require_routes)

    resp = client.post("/api/borrows/1/return")

    assert resp.status_code == 401


def test_create_borrow_book_not_found_404(client, admin_headers, db_session,
                                          make_reader, require_routes):
    _require_borrows(require_routes)
    reader = make_reader(name="读者甲", phone="13800000001")

    resp = client.post("/api/borrows", headers=admin_headers,
                       json={"book_id": 999999, "reader_id": reader.id})

    assert resp.status_code == 404


def test_create_borrow_reader_not_found_404(client, admin_headers, db_session,
                                            make_book, require_routes):
    _require_borrows(require_routes)
    book = make_book(title="图书", total_copies=2)

    resp = client.post("/api/borrows", headers=admin_headers,
                       json={"book_id": book.id, "reader_id": 999999})

    assert resp.status_code == 404


def test_get_borrow_not_found_404(client, admin_headers, require_routes):
    _require_borrows(require_routes)

    assert client.get("/api/borrows/999999", headers=admin_headers).status_code == 404


def test_return_borrow_not_found_404(client, admin_headers, require_routes):
    _require_borrows(require_routes)

    assert client.post("/api/borrows/999999/return", headers=admin_headers).status_code == 404
