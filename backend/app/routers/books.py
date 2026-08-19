from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import get_current_user
from backend.app.database.session import get_db
from backend.app.models.book import Book, utcnow
from backend.app.models.borrow import BorrowRecord
from backend.app.models.user import User
from backend.app.schemas.book import BookCreate, BookOut, BookUpdate
from backend.app.schemas.common import Page, make_page

router = APIRouter(prefix="/api/books", tags=["books"])


def _isbn_conflict() -> HTTPException:
    return HTTPException(status_code=409, detail="ISBN 已存在")


def _validate_page(page_size: int | None) -> int:
    settings = get_settings()
    size = page_size or settings.page_size_default
    if size > settings.page_size_max:
        raise HTTPException(status_code=422, detail="page_size 超出允许范围")
    return size


@router.get("", response_model=Page[BookOut])
def list_books(
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=50),
    available_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    size = _validate_page(page_size)
    query = select(Book)
    count_query = select(func.count()).select_from(Book)
    if keyword:
        term = f"%{keyword.strip()}%"
        condition = or_(Book.title.ilike(term), Book.author.ilike(term), Book.isbn.ilike(term))
        query = query.where(condition)
        count_query = count_query.where(condition)
    if category:
        condition = Book.category == category.strip()
        query = query.where(condition)
        count_query = count_query.where(condition)
    if available_only:
        query = query.where(Book.available_copies > 0)
        count_query = count_query.where(Book.available_copies > 0)
    total = db.scalar(count_query) or 0
    items = db.scalars(query.order_by(Book.id.desc()).offset((page - 1) * size).limit(size)).all()
    return make_page(items, total, page, size)


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    payload: BookCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    book = Book(**payload.model_dump(), available_copies=payload.total_copies)
    db.add(book)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _isbn_conflict()
    db.refresh(book)
    return book


@router.get("/{book_id}", response_model=BookOut)
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="图书不存在")
    return book


@router.put("/{book_id}", response_model=BookOut)
def update_book(
    book_id: int,
    payload: BookUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="图书不存在")
    values = payload.model_dump(exclude_unset=True)
    if "total_copies" in values:
        delta = values["total_copies"] - book.total_copies
        if book.available_copies + delta < 0:
            raise HTTPException(status_code=409, detail="总库存不能低于当前借出数量")
        book.available_copies += delta
    for field, value in values.items():
        if field != "total_copies":
            setattr(book, field, value)
    if "total_copies" in values:
        book.total_copies = values["total_copies"]
    book.updated_at = utcnow()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _isbn_conflict()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="图书不存在")
    has_history = db.scalar(
        select(func.count()).select_from(BorrowRecord).where(BorrowRecord.book_id == book_id)
    )
    if has_history:
        raise HTTPException(status_code=409, detail="存在借阅历史的图书不能删除")
    db.delete(book)
    db.commit()
