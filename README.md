# Material Bin 用户认证 API

基于FastAPI的用户认证模块，采用MVC架构，支持加密存储和会话管理。

## 特性

- 🔐 用户注册和登录（支持SHA256+bcrypt双重加密）
- 🛡️ 基于PBKDF2+AES的用户密钥管理
- 🎫 JWT令牌和会话管理
- 📋 用户CRUD操作
- 🏗️ MVC架构设计
- 📊 SQLite/MySQL数据库兼容
- 🚀 FastAPI + Pydantic + SQLAlchemy

## 项目结构

```
├── app/
│   ├── controllers/        # 控制器层 - API路由
│   ├── services/          # 服务层 - 业务逻辑
│   ├── models/           # 模型层 - 数据库模型
│   ├── schemas/          # Pydantic模型
│   └── core/            # 核心配置和工具
├── config/              # 配置管理
├── main.py             # 应用入口
├── pyproject.toml      # 项目配置
└── .env.example       # 环境变量示例
```

## 快速开始

### 1. 环境准备

确保已安装Python 3.12+和uv包管理器。

### 2. 项目设置

```bash
# 复制环境变量配置
cp .env.example .env

# 编辑.env文件，设置您的配置
# 特别注意修改SECRET_KEY为生产环境的安全密钥
```

### 3. 启动应用

```bash
# 启动开发服务器
uv run python main.py

# 或者使用uvicorn
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/api/health

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

### 会话管理

- `GET /api/users/{user_id}/sessions` - 获取用户会话
- `DELETE /api/users/sessions/{session_id}` - 撤销会话
- `POST /api/users/cleanup-sessions` - 清理过期会话

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
默认使用SQLite数据库，文件位置：`./user_auth.db`

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