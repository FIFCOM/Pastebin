# Material Bin

一个带 Material Design 风格 Web UI 的 Pastebin：后端基于 FastAPI（MVC 架构），支持用户认证、加密存储、文件上传与分享等能力；前端位于 `web/`（Vue 3 + Vite）。

## 特性

- 🔐 用户注册/登录（SHA256 + bcrypt 双重加密）
- 🎫 JWT 令牌与会话管理
- 🧾 Paste 创建/发布/查看（支持 Markdown / 纯文本）
- 🔒 客户端加密分享链接：加密密钥放在 URL hash（`/p/:id#key`），不会被浏览器发送给后端
- 📎 文件上传/下载（与 Paste 绑定）
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
├── web/                 # Web前端（Vue 3 + Vite）
│   ├── src/             # 页面、组件、路由、请求封装等
│   ├── public/          # 静态资源
│   └── vite.config.ts   # 开发代理等配置
├── main.py             # 应用入口
├── pyproject.toml      # 项目配置
└── .env.example       # 环境变量示例
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

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
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
- `/login`、`/register`：登录/注册

## API端点

### 用户认证

- `POST /api/users/register` - 用户注册
- `POST /api/users/login` - 用户登录

### 用户管理

- `GET /api/users/me` - 获取当前用户信息
- `GET /api/users/{user_id}` - 获取用户信息
- `PUT /api/users/{user_id}` - 更新用户信息
- `DELETE /api/users/{user_id}` - 删除用户
- `GET /api/users` - 获取用户列表
- `POST /api/users` - 创建用户（管理功能）

### 会话管理（用户）

- `GET /api/users/{user_id}/sessions` - 获取用户会话
- `DELETE /api/users/sessions/{session_id}` - 撤销会话
- `POST /api/users/cleanup-sessions` - 清理过期会话

### Paste

- `POST /api/pastes` - 创建Paste（草稿）
- `POST /api/pastes/{paste_id}/content` - 上传/更新内容（需要 `Bearer {admin_key}`）
- `POST /api/pastes/{paste_id}/publish` - 发布（需要 `Bearer {admin_key}`）
- `GET /api/pastes/{paste_id}` - 获取Paste信息（可选 `access_key`）
- `GET /api/pastes/{paste_id}/content` - 获取内容（可选 `access_key` / `encryption_key`）
- `POST /api/pastes/{paste_id}/files` - 上传文件（JSON，客户端加密；需要 `Bearer {admin_key}`）
- `POST /api/pastes/{paste_id}/files/upload` - 上传文件（multipart，服务端加密；需要 `Bearer {admin_key}`）
- `GET /api/pastes/{paste_id}/files/{file_id}` - 下载文件（可选 `encryption_key`）
- `DELETE /api/pastes/{paste_id}` - 删除Paste（需要 `Bearer {admin_key}`）

### 用户 History 管理

- `GET /api/user/history` - 获取用户Paste列表（需要登录）
- `POST /api/user/history/{paste_id}` - 保存Paste到用户（需要登录）
- `PUT /api/user/history/{paste_id}/star` - 收藏/取消收藏（需要登录）
- `DELETE /api/user/history/{paste_id}` - 从用户账户移除（需要登录）

### API Key 管理

- `GET /api/user/apikeys` - 列表（需要登录）
- `POST /api/user/apikeys` - 创建（需要登录）
- `DELETE /api/user/apikeys/{key_id}` - 删除（需要登录）

### 协作房间

- `POST /api/rooms/member-token` - 获取成员令牌（可匿名）
- `POST /api/rooms` - 创建房间（`Bearer {member_token}`）
- `GET /api/join/{pin_code}` - 通过PIN码获取房间信息
- `POST /api/rooms/{room_id}/join` - 加入房间（`Bearer {member_token}`）
- `GET /api/rooms/{room_id}/members` - 成员列表（`Bearer {member_token}`）
- `POST /api/rooms/{room_id}/pastes` - 分享Paste（`Bearer {member_token}`）
- `GET /api/rooms/{room_id}/pastes` - 房间Paste列表（`Bearer {member_token}`）
- `DELETE /api/rooms/{room_id}/leave` - 离开房间（`Bearer {member_token}`）

### 内部任务（需要内部令牌）

- `POST /api/internal/cleanup` - 执行清理任务（`Bearer {INTERNAL_TOKEN}`）
- `GET /api/internal/cleanup/status` - 清理服务状态（`Bearer {INTERNAL_TOKEN}`）

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
MYSQL_DATABASE_URL=mysql+pymysql://username:password@localhost:3306/material_bin
```

## 开发

### 代码格式化
```bash
uv run ruff format .
uv run ruff check .
```

### 数据库管理
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