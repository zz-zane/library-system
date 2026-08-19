"""图书端点契约测试（依据 ``docs/system-design.md`` §8.4 图书、§7 通用契约）。

覆盖：分页/筛选、唯一冲突（ISBN）、库存调整、删除保护、401/404/409/422 边界。
端点缺失时由 ``require_routes`` 标记预期失败；端点已存在时真实执行（不掩盖缺陷）。
"""

BOOKS_LIST_ROUTE = ("GET", "/api/books")
BOOKS_CREATE_ROUTE = ("POST", "/api/books")
BOOKS_GET_ROUTE = ("GET", "/api/books/{book_id}")
BOOKS_UPDATE_ROUTE = ("PUT", "/api/books/{book_id}")
BOOKS_DELETE_ROUTE = ("DELETE", "/api/books/{book_id}")

VALID_ISBN = "9780306406157"


def _require_books(require_routes):
    require_routes(
        {BOOKS_LIST_ROUTE, BOOKS_CREATE_ROUTE, BOOKS_GET_ROUTE, BOOKS_UPDATE_ROUTE, BOOKS_DELETE_ROUTE},
        "M2 图书端点未实现",
    )


# ---------------------------------------------------------------------------
# 正常路径
# ---------------------------------------------------------------------------


def test_list_books_returns_page(client, admin_headers, db_session, make_book, require_routes):
    """GET /api/books → 200 Page[BookOut] 结构（§7.2）。"""
    _require_books(require_routes)
    make_book(title="Python 编程", author="张三")

    resp = client.get("/api/books", headers=admin_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert {"items", "total", "page", "page_size", "pages"} <= set(data)
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    item = data["items"][0]
    assert item["title"] == "Python 编程"
    assert item["total_copies"] == item["available_copies"] == 1


def test_create_book_returns_201(client, admin_headers, require_routes):
    """POST /api/books → 201 BookOut，available=total（§8.4）。"""
    _require_books(require_routes)

    resp = client.post(
        "/api/books",
        headers=admin_headers,
        json={"title": "深入理解计算机系统", "author": "Randal E. Bryant",
              "isbn": VALID_ISBN, "total_copies": 3},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "深入理解计算机系统"
    assert data["isbn"] == VALID_ISBN
    assert data["total_copies"] == 3
    assert data["available_copies"] == 3


def test_get_book_returns_200(client, admin_headers, db_session, make_book, require_routes):
    _require_books(require_routes)
    book = make_book(title="获取图书", isbn=VALID_ISBN)

    resp = client.get(f"/api/books/{book.id}", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json()["id"] == book.id


def test_update_book_total_copies_adjusts_available(client, admin_headers, db_session,
                                                    make_book, require_routes):
    """PUT 总库存增加 → available 跟随调整（§8.4 库存更新规则）。"""
    _require_books(require_routes)
    book = make_book(title="库存调整", total_copies=3)  # available=3

    resp = client.put(f"/api/books/{book.id}", headers=admin_headers, json={"total_copies": 5})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_copies"] == 5
    assert data["available_copies"] == 5


def test_delete_book_without_history_204(client, admin_headers, db_session, make_book, require_routes):
    """无借阅历史的图书可删除 → 204（§8.4、D-15）。"""
    _require_books(require_routes)
    book = make_book(title="待删除")

    resp = client.delete(f"/api/books/{book.id}", headers=admin_headers)

    assert resp.status_code == 204
    assert client.get(f"/api/books/{book.id}", headers=admin_headers).status_code == 404


# ---------------------------------------------------------------------------
# 分页与筛选
# ---------------------------------------------------------------------------


def test_list_books_filter_by_keyword(client, admin_headers, db_session, make_book, require_routes):
    """keyword 同时匹配 title/author/isbn（§8.4）。"""
    _require_books(require_routes)
    make_book(title="Python 编程", author="张三")
    make_book(title="Java 编程", author="李四", isbn=VALID_ISBN)

    by_title = client.get("/api/books", headers=admin_headers, params={"keyword": "Python"})
    assert by_title.json()["total"] == 1
    assert by_title.json()["items"][0]["title"] == "Python 编程"

    by_author = client.get("/api/books", headers=admin_headers, params={"keyword": "李四"})
    assert by_author.json()["total"] == 1
    assert by_author.json()["items"][0]["title"] == "Java 编程"

    by_isbn = client.get("/api/books", headers=admin_headers, params={"keyword": "9780306406157"})
    assert by_isbn.json()["total"] == 1


def test_list_books_filter_by_category(client, admin_headers, db_session, make_book, require_routes):
    _require_books(require_routes)
    make_book(title="图书A", category="计算机")
    make_book(title="图书B", category="文学")

    resp = client.get("/api/books", headers=admin_headers, params={"category": "计算机"})

    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["title"] == "图书A"


def test_list_books_filter_available_only(client, admin_headers, db_session, make_book, require_routes):
    """available_only=true 只返回可用库存 > 0 的图书（§8.4）。"""
    _require_books(require_routes)
    make_book(title="可借图书", total_copies=1)
    make_book(title="借空图书", total_copies=1, available_copies=0)

    resp = client.get("/api/books", headers=admin_headers, params={"available_only": "true"})

    assert resp.status_code == 200
    titles = [item["title"] for item in resp.json()["items"]]
    assert titles == ["可借图书"]


def test_list_books_page_bounds_422(client, admin_headers, require_routes):
    """分页边界：page=0、page_size=0/101 → 422（§7.2）。"""
    _require_books(require_routes)

    assert client.get("/api/books", headers=admin_headers, params={"page": 0}).status_code == 422
    assert client.get("/api/books", headers=admin_headers, params={"page_size": 0}).status_code == 422
    assert client.get("/api/books", headers=admin_headers, params={"page_size": 101}).status_code == 422


# ---------------------------------------------------------------------------
# 401 / 404
# ---------------------------------------------------------------------------


def test_list_books_without_token_401(client, require_routes):
    _require_books(require_routes)

    assert client.get("/api/books").status_code == 401


def test_create_book_without_token_401(client, require_routes):
    _require_books(require_routes)

    resp = client.post("/api/books", json={"title": "T", "author": "A"})

    assert resp.status_code == 401


def test_get_book_not_found_404(client, admin_headers, require_routes):
    _require_books(require_routes)

    assert client.get("/api/books/999999", headers=admin_headers).status_code == 404


def test_update_book_not_found_404(client, admin_headers, require_routes):
    _require_books(require_routes)

    resp = client.put("/api/books/999999", headers=admin_headers, json={"title": "改名"})

    assert resp.status_code == 404


def test_delete_book_not_found_404(client, admin_headers, require_routes):
    _require_books(require_routes)

    assert client.delete("/api/books/999999", headers=admin_headers).status_code == 404


# ---------------------------------------------------------------------------
# 409 唯一冲突 / 业务冲突
# ---------------------------------------------------------------------------


def test_create_book_duplicate_isbn_409(client, admin_headers, db_session, make_book, require_routes):
    """重复 ISBN → 409（§8.4）。"""
    _require_books(require_routes)
    make_book(title="已存在", isbn=VALID_ISBN)

    resp = client.post(
        "/api/books",
        headers=admin_headers,
        json={"title": "重复", "author": "作者", "isbn": VALID_ISBN},
    )

    assert resp.status_code == 409


def test_delete_book_with_history_409(client, admin_headers, db_session, make_book,
                                     make_reader, make_user, make_borrow, require_routes):
    """存在借阅历史的图书禁止删除 → 409（§8.4、D-15）。"""
    _require_books(require_routes)
    book = make_book(title="有历史", total_copies=2)
    reader = make_reader(name="读者甲", phone="13800000001")
    user = make_user(username="librarian", password="password123")
    make_borrow(book_id=book.id, reader_id=reader.id, borrowed_by=user.id)

    resp = client.delete(f"/api/books/{book.id}", headers=admin_headers)

    assert resp.status_code == 409


def test_update_book_inventory_below_borrowed_409(client, admin_headers, db_session,
                                                  make_book, make_reader, require_routes):
    """总库存不能低于当前借出数量 → 409（§8.4 库存更新规则）。"""
    _require_books(require_routes)
    book = make_book(title="高库存", total_copies=3)
    reader = make_reader(name="读者甲", phone="13800000001")
    for _ in range(2):
        r = client.post("/api/borrows", headers=admin_headers,
                        json={"book_id": book.id, "reader_id": reader.id})
        assert r.status_code == 201
    # available = 1；total 降到 1 → new_available = 1 + (1-3) = -1 < 0
    resp = client.put(f"/api/books/{book.id}", headers=admin_headers, json={"total_copies": 1})

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 422 校验边界
# ---------------------------------------------------------------------------


def test_create_book_invalid_isbn_422(client, admin_headers, require_routes):
    """非法 ISBN（校验位/长度/格式）→ 422（§5.4、§8.4）。"""
    _require_books(require_routes)

    for bad_isbn in ["1234567890123", "12345", "9780306406158", "not-an-isbn"]:
        resp = client.post(
            "/api/books",
            headers=admin_headers,
            json={"title": "T", "author": "A", "isbn": bad_isbn},
        )
        assert resp.status_code == 422, f"isbn={bad_isbn} 应返回 422"


def test_create_book_missing_title_422(client, admin_headers, require_routes):
    _require_books(require_routes)

    resp = client.post("/api/books", headers=admin_headers, json={"author": "A"})

    assert resp.status_code == 422


def test_create_book_invalid_total_copies_422(client, admin_headers, require_routes):
    """total_copies 越界（0 或 1000）→ 422（§5.4 1–999）。"""
    _require_books(require_routes)

    for bad in [0, 1000]:
        resp = client.post(
            "/api/books", headers=admin_headers,
            json={"title": "T", "author": "A", "total_copies": bad},
        )
        assert resp.status_code == 422


def test_create_book_unknown_field_422(client, admin_headers, require_routes):
    """未知请求字段 → 422（§7.1）。"""
    _require_books(require_routes)

    resp = client.post(
        "/api/books", headers=admin_headers,
        json={"title": "T", "author": "A", "stock": 5},
    )

    assert resp.status_code == 422


def test_update_book_empty_body_422(client, admin_headers, db_session, make_book, require_routes):
    """BookUpdate 至少提供一项；空更新 → 422（§8.4）。"""
    _require_books(require_routes)
    book = make_book(title="空更新")

    resp = client.put(f"/api/books/{book.id}", headers=admin_headers, json={})

    assert resp.status_code == 422
