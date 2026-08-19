from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import get_current_user, get_password_hash
from backend.app.database.session import get_db
from backend.app.models.user import User, utcnow
from backend.app.schemas.common import Page, make_page
from backend.app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


def _duplicate_username() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")


@router.get("", response_model=Page[UserOut])
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    username: str | None = Query(default=None, max_length=64),
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    settings = get_settings()
    size = page_size or settings.page_size_default
    if size > settings.page_size_max:
        raise HTTPException(status_code=422, detail="page_size 超出允许范围")
    query = select(User)
    count_query = select(func.count()).select_from(User)
    if username:
        term = username.strip()
        query = query.where(User.username.ilike(f"%{term}%"))
        count_query = count_query.where(User.username.ilike(f"%{term}%"))
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    total = db.scalar(count_query) or 0
    items = db.scalars(query.order_by(User.id.desc()).offset((page - 1) * size).limit(size)).all()
    return make_page(items, total, page, size)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    user = User(
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        display_name=payload.display_name,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _duplicate_username()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="操作员不存在")

    if payload.is_active is False and user.id == current_user.id:
        raise HTTPException(status_code=409, detail="不能停用当前登录账号")
    if payload.is_active is False and user.is_active:
        active_count = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
        if active_count <= 1:
            raise HTTPException(status_code=409, detail="不能停用最后一个启用的操作员")

    fields = payload.model_fields_set
    if "display_name" in fields:
        user.display_name = payload.display_name
    if "password" in fields and payload.password is not None:
        user.password_hash = get_password_hash(payload.password)
    if "is_active" in fields and payload.is_active is not None:
        user.is_active = payload.is_active
    user.updated_at = utcnow()
    db.commit()
    db.refresh(user)
    return user
