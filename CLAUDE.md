# CLAUDE.md

## 项目概况

「图书管理员系统」是一个基于 Web 的图书管理平台，支持用户登录、图书管理和借阅管理三大核心功能。

## 角色与工作树体系

本项目由四个角色协作开发。GPT Sol 位于主工作树，负责总体设计与整合；其余角色在各自工作树和分支中完成专业任务。

| 角色 | 协作者 | 工作树 | 分支 | 职责范围 |
|------|--------|--------|------|----------|
| 🏗️ 总设计师 | **GPT Sol**（当前主对话） | 主工作树 | `main` | 需求分析、总体架构、任务拆解与调度、接口决策、成果审核和跨模块整合 |
| ⚙️ 后端工程师 | **GPT Luna** | `gpt` | `zz-zane/back_GPT_luna` | FastAPI、SQLAlchemy、Pydantic、认证、数据库与后端 API 开发 |
| 🎨 前端工程师 | **Kimi** | `great` | `zz-zane/for_kimi` | Vue 3、TypeScript、Element Plus、Pinia、Vue Router 与前端交互开发 |
| 🧪 测试工程师 | **DeepSeek** | `tester_deepseek` | `zz-zane/tester_deepseek` | pytest 测试策略、单元与集成测试、缺陷复现、回归验证和质量报告 |

详细职责、协作边界及分支约定见 `docs/agent-responsibilities.md`。

## 技术架构

```
┌─────────────────────────────────────────┐
│  Frontend (Vue 3 + Element Plus)        │
│  http://127.0.0.1:5173                  │
├─────────────────────────────────────────┤
│  Backend (FastAPI)                      │
│  http://127.0.0.1:8000                  │
├─────────────────────────────────────────┤
│  Database (SQLite)                      │
│  database/library.db                    │
└─────────────────────────────────────────┘
```

### 后端
- **框架**: FastAPI，Python 虚拟环境位于 `.venv/`
- **ORM**: SQLAlchemy 2.0，声明式模型基类 `Base` 定义在 `backend/app/database/session.py`
- **配置**: `pydantic-settings`，通过 `.env` 文件加载，默认值在 `backend/app/core/config.py`
- **认证**: 计划使用 JWT (python-jose) + passlib 密码哈希
- **数据库**: 当前使用 SQLite (`database/library.db`)，后续可迁移至 PostgreSQL

### 前端
- **框架**: Vue 3 Composition API，`<script setup>` 语法
- **语言**: TypeScript
- **构建**: Vite 7，监听 `127.0.0.1:5173`
- **UI 库**: Element Plus (已注册全局)
- **状态管理**: Pinia
- **路由**: Vue Router 4

### 测试
- **框架**: pytest
- **测试类型**: 配置单元测试 + API 集成测试 (TestClient)
- **位置**: `tests/` 目录

## 关键文件索引

| 文件 | 作用 |
|------|------|
| `backend/app/main.py` | FastAPI 应用工厂，CORS 配置 |
| `backend/app/core/config.py` | Settings 类与环境变量 |
| `backend/app/database/session.py` | SQLAlchemy 引擎与会话 |
| `backend/app/routers/health.py` | 健康检查端点 |
| `frontend/src/main.ts` | Vue 应用入口 |
| `frontend/src/App.vue` | 根组件 |
| `frontend/vite.config.ts` | Vite 配置 |

## 开发工作流

1. **GPT Sol（总设计师）**分析需求，制定总体方案、接口契约与验收标准。
2. GPT Sol 将后端任务分派给 **GPT Luna**，前端任务分派给 **Kimi**，测试任务分派给 **DeepSeek**。
3. 各专业协作者在自己的工作树与分支中设计、实现和自检，不直接修改其他角色负责的模块。
4. 涉及跨模块接口或职责边界的变更，先交由 GPT Sol 决策，再由对应角色实施。
5. GPT Sol 审核并整合前后端成果，DeepSeek 执行独立测试与回归验证，最终由 GPT Sol 确认验收。

## 注意事项

- 虚拟环境路径：`.venv/`（Windows）
- 前端开发服务器：`http://127.0.0.1:5173`
- 后端开发服务器：`http://127.0.0.1:8000`
- `.env` 文件从 `.env.example` 复制而来，不上传到 Git
