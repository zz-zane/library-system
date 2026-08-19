"""create library domain tables

Revision ID: 0001_create_library_domain_tables
Revises:
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_create_library_domain_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)

    op.create_table(
        "readers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_readers_name", "readers", ["name"], unique=False)
    op.create_index("ix_readers_status", "readers", ["status"], unique=False)

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("author", sa.String(length=100), nullable=False),
        sa.Column("isbn", sa.String(length=20), nullable=True),
        sa.Column("publisher", sa.String(length=200), nullable=True),
        sa.Column("publish_year", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("total_copies", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("available_copies", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("isbn"),
    )
    op.create_index("ix_books_title", "books", ["title"], unique=False)
    op.create_index("ix_books_author", "books", ["author"], unique=False)
    op.create_index("ix_books_category", "books", ["category"], unique=False)

    op.create_table(
        "borrow_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("reader_id", sa.Integer(), nullable=False),
        sa.Column("borrowed_by", sa.Integer(), nullable=False),
        sa.Column("borrowed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("returned_by", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reader_id"], ["readers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["borrowed_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["returned_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_borrow_records_book_id", "borrow_records", ["book_id"], unique=False)
    op.create_index("ix_borrow_records_reader_id", "borrow_records", ["reader_id"], unique=False)
    op.create_index("ix_borrow_records_returned_at", "borrow_records", ["returned_at"], unique=False)
    op.create_index("ix_borrow_records_due_date", "borrow_records", ["due_date"], unique=False)
    op.create_index(
        "ix_borrow_records_reader_returned",
        "borrow_records",
        ["reader_id", "returned_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_borrow_records_reader_returned", table_name="borrow_records")
    op.drop_index("ix_borrow_records_due_date", table_name="borrow_records")
    op.drop_index("ix_borrow_records_returned_at", table_name="borrow_records")
    op.drop_index("ix_borrow_records_reader_id", table_name="borrow_records")
    op.drop_index("ix_borrow_records_book_id", table_name="borrow_records")
    op.drop_table("borrow_records")
    op.drop_index("ix_books_category", table_name="books")
    op.drop_index("ix_books_author", table_name="books")
    op.drop_index("ix_books_title", table_name="books")
    op.drop_table("books")
    op.drop_index("ix_readers_status", table_name="readers")
    op.drop_index("ix_readers_name", table_name="readers")
    op.drop_table("readers")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
