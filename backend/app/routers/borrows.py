from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session, joinedload

from backend.app.core.config import get_settings
from backend.app.core.security import get_current_user
from backend.app.database.session import get_db
from backend.app.models.book import Book
from backend.app.models.borrow import BorrowRecord
from backend.app.models.reader import Reader
from backend.app.models.user import User
from backend.app.schemas.borrow import BorrowCreate, BorrowOut
from backend.app.schemas.common import Page, make_page

router = APIRouter(prefix="/api/borrows", tags=["borrows"])


def _status(record: BorrowRecord, today: date | None = None) -> str:
    if record.returned_at is not None:
        return "returned"
    return "overdue" if record.due_date < (today or date.today()) else "borrowed"


def _to_out(record: BorrowRecord) -> BorrowOut:
    return BorrowOut(
        id=record.id,
        book=record.book,
        reader=record.reader,
        borrowed_by=record.borrowed_by_user,
        borrowed_at=record.borrowed_at,
        due_date=record.due_date,
        returned_at=record.returned_at,
        returned_by=record.returned_by_user,
        status=_status(record),
        notes=record.notes,
    )


def _validate_page(page_size: int | None) -> int:
    settings = get_settings()
    size = page_size or settings.page_size_default
    if size > settings.page_size_max:
        raise HTTPException(status_code=422, detail="page_size 超出允许范围")
    return size


def _record_query():
    return select(BorrowRecord).options(
        joinedload(BorrowRecord.book),
        joinedload(BorrowRecord.reader),
        joinedload(BorrowRecord.borrowed_by_user),
        joinedload(BorrowRecord.returned_by_user),
    )


@router.get("", response_model=Page[BorrowOut])
def list_borrows(
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    status_filter: Literal["borrowed", "overdue", "returned"] | None = Query(
        default=None, alias="status"
    ),
    book_id: int | None = Query(default=None, gt=0),
    reader_id: int | None = Query(default=None, gt=0),
    due_before: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    size = _validate_page(page_size)
    today = date.today()
    query = _record_query()
    count_query = select(func.count()).select_from(BorrowRecord)
    conditions = []
    if status_filter == "returned":
        conditions.append(BorrowRecord.returned_at.is_not(None))
    elif status_filter == "overdue":
        conditions.extend(
            [BorrowRecord.returned_at.is_(None), BorrowRecord.due_date < today]
        )
    elif status_filter == "borrowed":
        conditions.extend(
            [BorrowRecord.returned_at.is_(None), BorrowRecord.due_date >= today]
        )
    if book_id is not None:
        conditions.append(BorrowRecord.book_id == book_id)
    if reader_id is not None:
        conditions.append(BorrowRecord.reader_id == reader_id)
    if due_before is not None:
        conditions.append(BorrowRecord.due_date <= due_before)
    if conditions:
        query = query.where(*conditions)
        count_query = count_query.where(*conditions)
    total = db.scalar(count_query) or 0
    records = db.scalars(
        query.order_by(BorrowRecord.id.desc()).offset((page - 1) * size).limit(size)
    ).unique().all()
    return make_page([_to_out(record) for record in records], total, page, size)


@router.post("", response_model=BorrowOut, status_code=status.HTTP_201_CREATED)
def create_borrow(
    payload: BorrowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    settings = get_settings()
    due_date = payload.due_date or today + timedelta(days=settings.borrow_days_default)
    if due_date < today:
        raise HTTPException(status_code=422, detail="due_date 不能早于当前日期")

    book = db.get(Book, payload.book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="图书不存在")
    reader = db.get(Reader, payload.reader_id)
    if reader is None:
        raise HTTPException(status_code=404, detail="读者不存在")
    if reader.status != "active":
        raise HTTPException(status_code=409, detail="停用读者不能借阅")

    overdue = db.scalar(
        select(func.count())
        .select_from(BorrowRecord)
        .where(
            BorrowRecord.reader_id == reader.id,
            BorrowRecord.returned_at.is_(None),
            BorrowRecord.due_date < today,
        )
    )
    if overdue:
        raise HTTPException(status_code=409, detail="读者存在逾期未还记录")
    active_count = db.scalar(
        select(func.count())
        .select_from(BorrowRecord)
        .where(BorrowRecord.reader_id == reader.id, BorrowRecord.returned_at.is_(None))
    ) or 0
    if active_count >= settings.max_concurrent_borrows:
        raise HTTPException(status_code=409, detail="读者已达到同时借阅上限")

    result = db.execute(
        update(Book)
        .where(Book.id == book.id, Book.available_copies > 0)
        .values(available_copies=Book.available_copies - 1)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="图书库存不足")

    record = BorrowRecord(
        book_id=book.id,
        reader_id=reader.id,
        borrowed_by=current_user.id,
        due_date=due_date,
        notes=payload.notes,
    )
    db.add(record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    record = db.scalar(_record_query().where(BorrowRecord.id == record.id))
    return _to_out(record)


@router.get("/{borrow_id}", response_model=BorrowOut)
def get_borrow(
    borrow_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    record = db.scalar(_record_query().where(BorrowRecord.id == borrow_id))
    if record is None:
        raise HTTPException(status_code=404, detail="借阅记录不存在")
    return _to_out(record)


@router.post("/{borrow_id}/return", response_model=BorrowOut)
def return_borrow(
    borrow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.scalar(
        select(BorrowRecord)
        .options(joinedload(BorrowRecord.book), joinedload(BorrowRecord.reader), joinedload(BorrowRecord.borrowed_by_user))
        .where(BorrowRecord.id == borrow_id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="借阅记录不存在")
    if record.returned_at is not None:
        raise HTTPException(status_code=409, detail="借阅记录已归还")

    result = db.execute(
        update(Book)
        .where(Book.id == record.book_id, Book.available_copies < Book.total_copies)
        .values(available_copies=Book.available_copies + 1)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=500, detail="库存数据不一致")
    record.returned_at = datetime.now(timezone.utc)
    record.returned_by = current_user.id
    db.commit()
    record = db.scalar(_record_query().where(BorrowRecord.id == borrow_id))
    return _to_out(record)
