from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import get_current_user
from backend.app.database.session import get_db
from backend.app.models.borrow import BorrowRecord
from backend.app.models.reader import Reader, utcnow
from backend.app.models.user import User
from backend.app.schemas.common import Page, make_page
from backend.app.schemas.reader import ReaderCreate, ReaderOut, ReaderUpdate

router = APIRouter(prefix="/api/readers", tags=["readers"])


def _contact_conflict() -> HTTPException:
    return HTTPException(status_code=409, detail="电话或邮箱已存在")


def _validate_page(page_size: int | None) -> int:
    settings = get_settings()
    size = page_size or settings.page_size_default
    if size > settings.page_size_max:
        raise HTTPException(status_code=422, detail="page_size 超出允许范围")
    return size


@router.get("", response_model=Page[ReaderOut])
def list_readers(
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=254),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|disabled)$"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    size = _validate_page(page_size)
    query = select(Reader)
    count_query = select(func.count()).select_from(Reader)
    if keyword:
        term = f"%{keyword.strip()}%"
        condition = or_(Reader.name.ilike(term), Reader.phone.ilike(term), Reader.email.ilike(term))
        query = query.where(condition)
        count_query = count_query.where(condition)
    if status_filter:
        query = query.where(Reader.status == status_filter)
        count_query = count_query.where(Reader.status == status_filter)
    total = db.scalar(count_query) or 0
    items = db.scalars(query.order_by(Reader.id.desc()).offset((page - 1) * size).limit(size)).all()
    return make_page(items, total, page, size)


@router.post("", response_model=ReaderOut, status_code=status.HTTP_201_CREATED)
def create_reader(
    payload: ReaderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    reader = Reader(**payload.model_dump(), status="active")
    db.add(reader)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _contact_conflict()
    db.refresh(reader)
    return reader


@router.get("/{reader_id}", response_model=ReaderOut)
def get_reader(
    reader_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    reader = db.get(Reader, reader_id)
    if reader is None:
        raise HTTPException(status_code=404, detail="读者不存在")
    return reader


@router.put("/{reader_id}", response_model=ReaderOut)
def update_reader(
    reader_id: int,
    payload: ReaderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    reader = db.get(Reader, reader_id)
    if reader is None:
        raise HTTPException(status_code=404, detail="读者不存在")
    values = payload.model_dump(exclude_unset=True)
    next_phone = values.get("phone", reader.phone)
    next_email = values.get("email", reader.email)
    if not next_phone and not next_email:
        raise HTTPException(status_code=422, detail="phone 或 email 至少填写一项")
    for field, value in values.items():
        setattr(reader, field, value)
    reader.updated_at = utcnow()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _contact_conflict()
    db.refresh(reader)
    return reader


@router.delete("/{reader_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reader(
    reader_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    reader = db.get(Reader, reader_id)
    if reader is None:
        raise HTTPException(status_code=404, detail="读者不存在")
    has_history = db.scalar(
        select(func.count()).select_from(BorrowRecord).where(BorrowRecord.reader_id == reader_id)
    )
    if has_history:
        raise HTTPException(status_code=409, detail="存在借阅历史的读者不能删除")
    db.delete(reader)
    db.commit()
