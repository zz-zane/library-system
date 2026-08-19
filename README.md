# 图书管理员系统

一个基于 FastAPI、Vue 3 和 SQLite 的开源图书管理平台，提供操作员认证、图书管理、读者管理和借阅管理功能。

## 功能

- JWT 操作员登录与账号管理
- 图书检索、新增、编辑、库存管理和受保护删除
- 读者检索、新增、编辑、停用和受保护删除
- 借出、归还、逾期判断、借阅上限和库存一致性校验
- Vue 3 + Element Plus 管理界面
- Alembic 数据库迁移与 pytest 契约测试

## 技术栈

- 后端：FastAPI、SQLAlchemy 2.0、Pydantic、Alembic
- 前端：Vue 3、TypeScript、Element Plus、Pinia、Vue Router、Vite
- 数据库：SQLite（模型保持 PostgreSQL 可迁移性）
- 测试：pytest、FastAPI TestClient

## 本地运行

### 1. 配置环境

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

将生成的随机值写入 `.env` 的 `SECRET_KEY`，并设置仅用于初始化操作员的 `ADMIN_USERNAME` 与 `ADMIN_PASSWORD`。不要提交 `.env`。

### 2. 启动后端

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head
.venv/Scripts/python -m backend.scripts.seed_admin
.venv/Scripts/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Windows PowerShell 可将 `.venv/Scripts/python` 替换为 `.venv\Scripts\python.exe`。

### 3. 启动前端

```bash
pnpm --dir frontend install
pnpm --dir frontend dev
```

打开 <http://127.0.0.1:5173>。API 文档位于 <http://127.0.0.1:8000/docs>。

## 验证

```bash
.venv/Scripts/python -m pytest -q
pnpm --dir frontend build
```

## 安全说明

- `SECRET_KEY` 必须由安全随机源生成，每个部署使用不同值。
- 不要提交 `.env`、SQLite 数据库、授权码、API 密钥或真实读者数据。
- MVP 采用单一操作员角色；所有启用的操作员拥有相同管理能力。公网部署前应结合实际组织权限模型评估 RBAC、审计和限流需求。

详细设计与 API 契约见 [`docs/system-design.md`](docs/system-design.md)。

## License

本项目采用 [MIT License](LICENSE)。
