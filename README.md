# Multi-LLM Library System

> **More than a library management app — this repository is a working blueprint for multi-LLM software collaboration.**

本项目**不仅是一个可运行的图书管理系统，更是一套真实落地的多模型协作开发范例**。图书管理业务是验证载体，核心价值是展示 GPT Sol、GPT Luna、Kimi 与 DeepSeek 如何在独立 Git 工作树中完成需求冻结、专业分工、并行实现、独立测试、缺陷归因和受控整合，并通过“一文件一负责人”避免多个 Agent 同时修改同一文件造成的混乱。

## Multi-LLM Collaboration Logic

项目由一个协调者和三个专业子工作树组成：

| 角色 | 工作树职责 | 文件所有权 |
|---|---|---|
| **GPT Sol** | 总体设计、接口契约、任务拆解、审核与整合 | `main`、共享设计文档 |
| **GPT Luna** | FastAPI、SQLAlchemy、认证、数据库和后端 API | `backend/**` |
| **Kimi** | Vue 3 页面、路由、Pinia、API 调用和前端构建 | `frontend/**` |
| **DeepSeek** | pytest 基础设施、契约测试、缺陷归因与回归验证 | `tests/**` |

协作流程遵循以下规则：

1. GPT Sol 先冻结需求、数据模型、API 和验收标准，再派发具体任务。
2. 每个文件只归一个角色负责，三个子工作树不跨目录修改，避免并发覆盖和合并错乱。
3. GPT Luna、Kimi 和 DeepSeek 在各自分支中自行配置环境、实现、验证并提交。
4. 后端、前端和测试可以在目录边界内并行工作；存在依赖时按测试结果串行修复。
5. GPT Sol 只审核提交范围和结果，将通过验证的提交整合进 `main`，不代替专业 Agent 修改其文件。
6. 整合后统一运行 pytest 和前端生产构建；失败由对应文件 Owner 修复，再进入下一轮。

这种方式把多模型协作变成可审计的 **contract → isolated implementation → independent verification → controlled integration** 流程。

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
