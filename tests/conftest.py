"""pytest 共享 fixture 与 API 测试基础设施。

依据 ``docs/system-design.md`` §13.2「测试隔离」建立：

- **隔离 SQLite**：``StaticPool`` 内存数据库，每个测试完整重建 schema，
  禁止触碰 ``database/library.db``（D-10：测试可使用 ``metadata.create_all()``）；
- **依赖覆盖**：通过 FastAPI ``dependency_overrides`` 覆盖后端 ``get_db``；
- **鉴权辅助**：``make_access_token`` / ``bearer_headers`` / ``active_user`` /
  ``admin_headers``，以及路由存在性探测（``route_map`` / ``require_routes``）；
- **数据工厂**：``make_user`` / ``make_book`` / ``make_reader`` / ``make_borrow``，
  面向 M2 后端模型（模型实现后自动可用）。

当前基线处于 M0 脚手架阶段，业务模型与路由尚未实现。数据工厂与鉴权辅助
依赖后端模型，在模型缺失时会抛出 ``ImportError``；由依赖它们的契约测试
通过 ``require_routes`` 标记为预期失败（xfail），如实记录而非掩盖缺陷。
"""

import os
from datetime import datetime, timedelta, timezone

# 必须在导入 backend 之前设置测试配置，确保
# backend.app.database.session 不会创建指向 database/library.db 的引擎。
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite://"
# 以下为测试专用密钥，仅用于生成测试 JWT，绝不用于任何生产环境。
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "1440"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings
from backend.app.database.session import Base, get_db
from backend.app.main import create_app

# 环境变量已设置，清理 settings 缓存使其生效。
get_settings.cache_clear()

# 测试专用引擎：内存 SQLite + StaticPool，同一连接上每个测试重建 schema。
TEST_SECRET_KEY = os.environ["SECRET_KEY"]
TEST_JWT_ALGORITHM = os.environ["JWT_ALGORITHM"]
_TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)


def _password_hash(password: str) -> str:
    """生成与后端完全一致的密码哈希。

    后端（backend/app/core/security.py）采用 ``sha256 预哈希 + bcrypt``，
    并已实测 ``passlib 1.7.4`` 与 ``bcrypt>=5`` 不兼容（passlib 哈希会抛
    ``ValueError: password cannot be longer than 72 bytes``）。因此这里直接
    复用后端 ``get_password_hash``，确保 make_user 写入的测试数据能被后端
    ``verify_password`` 正确验证。
    """
    from backend.app.core.security import get_password_hash

    return get_password_hash(password)


# ---------------------------------------------------------------------------
# 数据库隔离
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_engine():
    """会话级测试引擎（内存 SQLite，``StaticPool``）。"""
    return _TEST_ENGINE


@pytest.fixture(autouse=True)
def _isolated_schema(test_engine):
    """每个测试独立 schema：``drop_all + create_all`` 完整重建。

    后端业务模型实现后（M2）会注册到 ``Base.metadata``，本 fixture 自动生效。
    """
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture()
def db_session():
    """独立事务会话，供 ORM 数据工厂在测试内直接创建数据。"""
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    """覆盖 ``get_db`` 依赖的 FastAPI TestClient。

    所有业务路由通过 ``get_db()`` 获取会话（§10 复用要求），
    依赖覆盖后请求只会读写隔离的测试数据库。
    """
    app = create_app()

    def _override_get_db():
        db = _TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 路由存在性探测与契约测试标记
# ---------------------------------------------------------------------------


def _collect_routes(routes, acc):
    """递归收集 ``(method, path)`` 路由对。

    FastAPI 0.140 使用 ``_IncludedRouter`` 延迟展开 ``include_router`` 注册的路由，
    顶层 ``app.routes`` 中会直接出现该占位对象而非具体 ``Route``；需向下钻取
    ``original_router.routes`` 才能拿到真实的 ``path``/``methods``。
    """
    for route in routes:
        if type(route).__name__ == "_IncludedRouter":
            _collect_routes(route.original_router.routes, acc)
        else:
            for method in (getattr(route, "methods", None) or set()):
                acc.add((method, route.path))


@pytest.fixture(scope="session")
def route_map():
    """当前应用中已注册的 ``(method, path)`` 路由集合。

    用于判定业务端点是否已实现：端点缺失时契约测试标记为预期失败，
    后端实现后自动转为真实执行。
    """
    app = create_app()
    routes = set()
    _collect_routes(app.routes, routes)
    return routes


@pytest.fixture()
def require_routes(client):
    """端点未实现时以 ``pytest.xfail`` 标记预期失败，实现后测试真实执行。

    基于被测 ``client.app`` 实时探测路由：既能看到应用自身注册的端点，
    也能感知测试运行期间动态注册的端点（如模拟后端或临时 stub）。
    """

    def _require(routes, reason):
        live = set()
        _collect_routes(client.app.routes, live)
        missing = set(routes) - live
        if missing:
            pytest.xfail(f"{reason}（当前缺失端点：{sorted(missing)}）")

    return _require


# ---------------------------------------------------------------------------
# 鉴权辅助
# ---------------------------------------------------------------------------


@pytest.fixture()
def make_access_token():
    """构造测试 JWT（python-jose），payload 遵循设计文档 §6.2 契约。"""

    def _make(sub, username="tester", secret_key=None, algorithm=None,
              expires_delta=timedelta(minutes=30)):
        from jose import jwt

        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(sub),
            "username": username,
            "type": "access",
            "iat": now.timestamp(),
            "exp": (now + expires_delta).timestamp(),
        }
        return jwt.encode(
            payload,
            secret_key or TEST_SECRET_KEY,
            algorithm=algorithm or TEST_JWT_ALGORITHM,
        )

    return _make


@pytest.fixture()
def bearer_headers():
    """构造 ``Authorization: Bearer <token>`` 请求头。"""

    def _headers(token):
        return {"Authorization": f"Bearer {token}"}

    return _headers


# ---------------------------------------------------------------------------
# 数据工厂（面向 M2 后端模型）
# ---------------------------------------------------------------------------


@pytest.fixture()
def make_user(db_session):
    """ORM 创建操作员（依赖后端 ``User`` 模型，M2 实现后可用）。"""

    def _make(username="librarian", password="password123", display_name=None,
              is_active=True, **extra):
        from backend.app.models.user import User

        now = datetime.now(timezone.utc)
        user = User(
            username=username,
            password_hash=_password_hash(password),
            display_name=display_name or username,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            **extra,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture()
def make_book(db_session):
    """ORM 创建图书（依赖后端 ``Book`` 模型，M2 实现后可用）。"""

    def _make(title="测试图书", author="测试作者", isbn=None, total_copies=1,
              available_copies=None, **extra):
        from backend.app.models.book import Book

        now = datetime.now(timezone.utc)
        book = Book(
            title=title,
            author=author,
            isbn=isbn,
            total_copies=total_copies,
            available_copies=total_copies if available_copies is None else available_copies,
            created_at=now,
            updated_at=now,
            **extra,
        )
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)
        return book

    return _make


@pytest.fixture()
def make_reader(db_session):
    """ORM 创建读者（依赖后端 ``Reader`` 模型，M2 实现后可用）。"""

    def _make(name="测试读者", phone=None, email=None, status="active", **extra):
        from backend.app.models.reader import Reader

        now = datetime.now(timezone.utc)
        reader = Reader(
            name=name,
            phone=phone,
            email=email,
            status=status,
            created_at=now,
            updated_at=now,
            **extra,
        )
        db_session.add(reader)
        db_session.commit()
        db_session.refresh(reader)
        return reader

    return _make


@pytest.fixture()
def make_borrow(db_session):
    """ORM 创建借阅记录（依赖后端 ``BorrowRecord`` 模型，M2 实现后可用）。"""

    def _make(book_id, reader_id, borrowed_by, due_date=None, **extra):
        from backend.app.models.borrow import BorrowRecord

        now = datetime.now(timezone.utc)
        record = BorrowRecord(
            book_id=book_id,
            reader_id=reader_id,
            borrowed_by=borrowed_by,
            borrowed_at=now,
            due_date=due_date or (now.date() + timedelta(days=30)),
            **extra,
        )
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        return record

    return _make


@pytest.fixture()
def active_user(make_user):
    """启用状态操作员（ORM 创建，面向未来；依赖后端模型）。"""
    return make_user(username="librarian", password="password123", display_name="管理员")


@pytest.fixture()
def admin_headers(make_user, make_access_token, bearer_headers, route_map):
    """已认证操作员的请求头（面向未来：依赖后端模型与 JWT 鉴权实现）。

    当前操作员端点或用户模型缺失时标记预期失败，避免契约测试在
    setup 阶段产生 ERROR 而非 XFAIL。
    """
    users_routes = {("GET", "/api/users"), ("POST", "/api/users"), ("PUT", "/api/users/{user_id}")}
    if not users_routes <= route_map:
        pytest.xfail("M2 操作员端点未实现，依赖认证头的测试预期失败")

    try:
        from backend.app.models.user import User  # noqa: F401
    except ImportError:
        pytest.xfail("M2 后端用户模型未实现，依赖认证头的测试预期失败")

    user = make_user(username="admin", password="password123", display_name="管理员")
    token = make_access_token(user.id, user.username)
    return bearer_headers(token)
