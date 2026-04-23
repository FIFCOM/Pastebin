# Material Bin

一个带 Material Design 风格 Web UI 的 Pastebin：后端基于 FastAPI（MVC 架构），支持用户认证、加密存储、文件上传与分享等能力；前端位于 `web/`（Vue 3 + Vite）。

## 特性

- 🔐 用户注册/登录（SHA256 + bcrypt 双重加密）
- 🎫 JWT 令牌与会话管理
- 🧾 Paste 创建/发布/查看（支持 Markdown / 纯文本）
- 🔒 客户端加密分享链接：加密密钥放在 URL hash（`/p/:id#key`），不会被浏览器发送给后端
- 📎 文件上传/下载（分片上传、可断点续传；与 Paste 绑定）
- 🔑 用户 API Key 管理
- 👥 协作房间（member token / 房间 / 加入 / 分享）
- 🧹 内部清理任务（草稿/过期内容/成员）
- 📊 SQLite / MySQL 数据库兼容
- 🚀 FastAPI + Pydantic + SQLAlchemy + Vue 3

## 项目结构

```
├── app/
│   ├── controllers/        # 控制器层 - API路由
│   ├── services/          # 服务层 - 业务逻辑
│   ├── models/           # 模型层 - 数据库模型
│   ├── schemas/          # Pydantic模型
│   └── core/            # 核心配置和工具
├── config/              # 配置管理
├── docker/              # 容器启动脚本
├── web/                 # Web前端（Vue 3 + Vite）
│   ├── src/             # 页面、组件、路由、请求封装等
│   ├── public/          # 静态资源
│   └── vite.config.ts   # 开发代理等配置
├── main.py             # 应用入口
├── Dockerfile          # 单镜像构建（后端 + 前端静态产物）
├── compose.yaml        # 默认 SQLite 部署
├── compose.mysql.yaml  # MySQL 覆盖配置
├── pyproject.toml      # 项目配置
├── .env.example        # 应用环境变量示例
└── .env.docker.example # Docker Compose 环境变量示例
```

## 快速开始

### 1. 环境准备（后端）

确保已安装Python 3.12+和uv包管理器。

### 2. 后端配置

```bash
# 复制环境变量配置
cp .env.example .env

# 编辑.env文件，设置您的配置
# 特别注意修改SECRET_KEY为生产环境的安全密钥
```

### 3. 启动后端

```bash
# 安装/同步依赖（推荐）
uv sync

# 启动开发服务器
uv run python main.py

# 或者使用uvicorn
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问API文档

- 前端文档页（Web）：http://localhost:5173/docs
- Swagger UI: http://localhost:8000/api/openapi/docs
- ReDoc: http://localhost:8000/api/openapi/redoc
- Markdown 原文接口：`GET /api/docs`、`GET /api/docs/{slug}`
- 健康检查: http://localhost:8000/api/health

### 5. 启动 Web（`web/`）

前端默认通过 Vite 代理 `/api` 到后端（推荐），对应配置项是 `VITE_BACKEND`。

```bash
cd web
npm install

# 可选：配置后端地址（用于 Vite dev proxy 的 target）
# macOS/Linux:
export VITE_BACKEND="http://localhost:8000"
# Windows PowerShell:
# $env:VITE_BACKEND="http://localhost:8000"

npm run dev
```

打开 Vite 输出的本地地址（默认类似 http://localhost:5173）。

前端页面路由：
- `/`：Paste 编辑/发布
- `/p/:paste_id`：Paste 查看（需要在 URL hash 携带密钥：`/p/:id#encryption_key`）
- `/docs`、`/docs/:section`：API 文档页面（内容由后端 `/api/docs*` 返回 Markdown 原文）
- `/login`、`/register`：登录/注册

## Docker 部署

项目现在支持用单个应用镜像部署，镜像会：

- 在构建阶段编译 `web/` 前端产物
- 在运行阶段由 FastAPI 直接托管 `web/dist`
- 启动前自动创建数据库表
- 默认使用 SQLite 持久化卷
- 可选接入独立 MySQL 容器
- 默认同时启动一个自动定时清理容器

### 1. 默认部署：SQLite

```bash
cp .env.docker.example .env.docker

docker compose --env-file .env.docker up -d --build
```

访问地址：

- 应用首页：http://localhost:8000/
- 健康检查：http://localhost:8000/api/health

默认情况下：

- `DB_DRIVER=sqlite`
- SQLite 文件位于容器内 `/app/data/material_bin.db`
- 上传文件与 SQLite 数据都落在 compose 卷 `materialbin_data`
- `materialbin-cleanup` 会每 `900` 秒自动执行一次 cleanup CLI

### 2. 可选部署：MySQL

```bash
cp .env.docker.example .env.docker

# 编辑 .env.docker，至少确认以下变量：
# DB_DRIVER=mysql
# MYSQL_DATABASE=material_bin
# MYSQL_USER=material_bin
# MYSQL_PASSWORD=material_bin
# MYSQL_ROOT_PASSWORD=materialbin-root-password

docker compose --env-file .env.docker -f compose.yaml -f compose.mysql.yaml up -d --build
```

此时：

- 应用容器会把 `DB_DRIVER` 切到 `mysql`
- `compose.mysql.yaml` 会额外启动 `mysql:8.4`
- 应用会自动等待 MySQL 健康后再初始化数据库表
- 自动清理容器会复用同一组 MySQL 连接配置

### 3. 容器环境变量说明

容器启动时支持两种数据库配置方式：

- 推荐方式：设置 `DB_DRIVER=sqlite|mysql`，再配合 `SQLITE_PATH` 或 `MYSQL_*`
- 直连方式：直接设置 `DATABASE_URL`，会覆盖 `DB_DRIVER` 的自动拼接逻辑

SQLite 默认值：

```env
DB_DRIVER=sqlite
SQLITE_PATH=/app/data/material_bin.db
DATA_DIR=/app/data
```

MySQL 默认拼接规则：

```env
DB_DRIVER=mysql
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=material_bin
MYSQL_USER=material_bin
MYSQL_PASSWORD=material_bin
```

对应生成：

```env
DATABASE_URL=mysql+pymysql://material_bin:material_bin@mysql:3306/material_bin
```

如果用户名或密码里包含 `@`、`:`、`/` 等特殊字符，建议直接显式设置 `DATABASE_URL`，避免 URL 编码问题。

自动清理相关环境变量：

```env
CLEANUP_INTERVAL_SECONDS=900
CLEANUP_RUN_ON_START=true
# 可选，留空表示执行全部清理任务；多个任务用空格分隔
# CLEANUP_TASKS=expired_drafts expired_pastes expired_members
```

### 4. 首次启动后的安装

容器会自动生成运行所需的 `.env` 标记文件并建表，但管理员账户仍需按项目原有安装流程完成：

1. 打开首页或 `/install`
2. 按向导确认配置
3. 创建第一个管理员账号

### 5. 常用命令

```bash
# 查看日志
docker compose logs -f materialbin

# 查看自动清理日志
docker compose logs -f materialbin-cleanup

# 停止服务
docker compose down

# SQLite 模式下连同数据卷一起删除
docker compose down -v

# MySQL 模式下删除所有相关卷
docker compose -f compose.yaml -f compose.mysql.yaml down -v
```

## API端点

### 安装态错误契约（HTTP 428）

当服务端检测到尚未完成安装（例如 `.env` 不存在或管理员未创建）时，除安装与健康检查白名单接口外，会返回 `428 Precondition Required`：

```json
{
  "error": "安装未完成",
  "detail": "安装未完成，请先完成安装",
  "status_code": 428,
  "code": "INSTALL_REQUIRED"
}
```

第三方客户端建议按以下顺序处理：
- 先判断 HTTP 状态码是否为 `428`
- 再判断响应 `code === "INSTALL_REQUIRED"`
- 命中后跳转或提示用户完成安装流程（Web 默认引导到 `/install`）

安装白名单路径（不会被安装门禁拦截）：
- `/api/install` 与 `/api/install/*`
- `/api/health` 与 `/api/health/`
- `/api/docs` 与 `/api/docs/*`
- `/api/openapi.json`
- `/api/openapi/docs`、`/api/openapi/redoc`

### 内部任务（需要内部令牌）

- `POST /api/internal/cleanup` - 执行清理任务（`X-Internal-Token: {INTERNAL_TOKEN}`）
- `GET /api/internal/cleanup/status` - 清理服务状态（`X-Internal-Token: {INTERNAL_TOKEN}`）

## 定时清理

项目内置了一个可直接用于定时任务的 cleanup CLI：

```bash
uv run python -m app.cleanup_cli --list-tasks
uv run python -m app.cleanup_cli
uv run python -m app.cleanup_cli expired_drafts expired_pastes expired_members
```

- 不传任务名时，会依次执行全部过期清理任务
- 返回码 `0` 表示全部成功，返回码 `1` 表示至少有一个任务失败
- 推荐在 cron 中使用绝对路径，并把输出重定向到日志文件

示例 cron：

```cron
*/15 * * * * /home/your-user/.local/bin/uv run python -m app.cleanup_cli >> /var/log/material-bin-cleanup.log 2>&1
15 2 * * * /home/your-user/.local/bin/uv run python -m app.cleanup_cli expired_members expired_pastes >> /var/log/material-bin-cleanup.log 2>&1
```

如果你的环境没有把 `uv` 放进 cron 可见的 `PATH`，请改成虚拟环境里的 Python 绝对路径：

```cron
*/15 * * * * /srv/material-bin/.venv/bin/python -m app.cleanup_cli >> /var/log/material-bin-cleanup.log 2>&1
```

### 其他

- `GET /api/health` - 健康检查

## 使用说明

### 用户注册

注册时需要提供：
- `email`: 用户邮箱
- `password`: SHA256哈希后的密码（64位十六进制字符串）

系统会：
1. 自动生成用户名（格式：USER_XXXXXXXX）
2. 使用bcrypt再次加密密码
3. 生成用户密钥并使用PBKDF2+AES加密存储

### 用户登录

登录时需要提供：
- `username`: 系统生成的用户名
- `password`: 与注册时相同的SHA256哈希密码

系统会：
1. 验证用户凭据
2. 恢复用户密钥
3. 创建会话和JWT令牌

### 密码安全

本系统采用双重加密：
1. 客户端：明文密码 → SHA256哈希
2. 服务端：SHA256哈希 → bcrypt加密存储

### 密钥管理

按照AGENT.md的规范：
1. 使用PBKDF2从密码和盐派生master_key
2. 生成随机encryption_key作为用户密钥
3. 使用master_key加密用户密钥存储
4. 登录时重新派生master_key并解密用户密钥

## 数据库

### SQLite（默认）
默认使用SQLite数据库，文件位置由 `DATABASE_URL` 决定（示例：`sqlite:///./material_bin.db`）

### MySQL
设置环境变量：
```
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/material_bin
```

Docker 部署时也可以不直接写 `DATABASE_URL`，而是使用 `DB_DRIVER=mysql` 配合 `MYSQL_HOST / MYSQL_PORT / MYSQL_DATABASE / MYSQL_USER / MYSQL_PASSWORD` 自动生成。

## 开发

### 代码格式化
```bash
uv run ruff format .
uv run ruff check .
```

### 数据库管理
服务启动时不会自动建表；首次安装会在创建管理员前自动执行建表。

```bash
# 初始化数据库
uv run python app/core/init_db.py

# 重置数据库
uv run python -c "from app.core.init_db import reset_database; reset_database()"
```

## 环境变量

参考`.env.example`文件中的所有可配置项。

## 安全注意事项

1. 生产环境必须修改`SECRET_KEY`
2. 限制CORS允许的域名
3. 使用HTTPS
4. 定期清理过期会话
5. 监控异常登录行为

## 许可证

MIT License
