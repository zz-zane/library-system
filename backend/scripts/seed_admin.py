from __future__ import annotations

import re
import sys

from backend.app.core.config import get_settings
from backend.app.core.security import get_password_hash
from backend.app.database.session import SessionLocal
from backend.app.models.user import User

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,64}$")


def main() -> int:
    settings = get_settings()
    username = settings.admin_username
    password = settings.admin_password
    if not username or not password:
        print("未配置 ADMIN_USERNAME 或 ADMIN_PASSWORD", file=sys.stderr)
        return 1
    if not _USERNAME_RE.fullmatch(username):
        print("ADMIN_USERNAME 格式无效", file=sys.stderr)
        return 1
    if not 8 <= len(password) <= 128:
        print("ADMIN_PASSWORD 长度必须为 8-128", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing is not None:
            print(f"操作员 {username} 已存在，未修改")
            return 0
        db.add(
            User(
                username=username,
                password_hash=get_password_hash(password),
                display_name=username,
                is_active=True,
            )
        )
        db.commit()
        print(f"已创建操作员 {username}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
