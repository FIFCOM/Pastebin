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
- `POST /api/pastes/{paste_id}/content` - 上传/更新内容（需要 `Bearer {admin_key}`；若为服务端加密且已发布，需额外提供 `X-Encryption-Key: {encryption_key}`）
- `POST /api/pastes/{paste_id}/publish` - 发布（需要 `Bearer {admin_key}`）
- `GET /api/pastes/{paste_id}` - 获取Paste信息（可选 `access_key`；文件列表请从 `/content` 获取）
- `GET /api/pastes/{paste_id}/content` - 获取内容与文件列表（可选 `access_key` / `encryption_key`）
- `POST /api/pastes/{paste_id}/files/init` - 初始化分片上传（JSON；返回 `upload_id/chunk_size/total_chunks`）
- `GET /api/pastes/{paste_id}/files/{upload_id}/status` - 获取分片上传状态（断点续传；返回已上传分片索引等）
- `PUT /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}` - 上传分片（二进制 `application/octet-stream`）
- `POST /api/pastes/{paste_id}/files/{upload_id}/complete` - 完成分片上传（创建最终文件记录）
- `POST /api/pastes/{paste_id}/files/{upload_id}/abort` - 取消并清理分片上传
- `GET /api/pastes/{paste_id}/files/{file_id}` - 下载文件（可选 `access_key` / `encryption_key`）
- `DELETE /api/pastes/{paste_id}` - 删除Paste（需要 `Bearer {admin_key}`）

## 文件上传加解密流程

### 共同约定

- 算法：`AES-GCM`
- 密钥长度：与后端 `ENCRYPTION_KEY_LENGTH` 一致（默认 `16` 字节 = AES-128；可配置 `24/32`）
- 密文格式：`encrypted_data = IV(12B) + ciphertext_and_tag`（tag 为 `16B`）
- 加密模式（`encryption_mode`）
  - `client`：客户端加密；服务端不持有解密密钥
  - `server`：服务端加密；草稿阶段服务端保存 `PasteKey`，发布后客户端持有 `encryption_key` 并在写入时通过 `X-Encryption-Key` 提供

### 接口：二进制分片上传（支持大文件）

#### 1) 初始化上传会话

`POST /api/pastes/{paste_id}/files/init`

服务端返回：
- `upload_id`：上传会话ID（也是最终 `file_id`）
- `chunk_size`：按“明文”计算的分片大小（最后一片可能更小）
- `total_chunks`：总分片数
- `aad_prefix / aad_required / iv_scheme`：加密协议参数（前后端必须一致）

#### 2) 上传每个分片（PUT 二进制）

`PUT /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}`（`Content-Type: application/octet-stream`）

后端期望长度：
- `expected_plain = index < total_chunks-1 ? chunk_size : file_size - chunk_size*(total_chunks-1)`
- `server` 模式：上传明文分片，长度必须为 `expected_plain`
- `client` 模式：上传加密分片，长度必须为 `expected_plain + 12 + 16`
  - 前端可用 `web/src/utils/crypto.ts:327` 的 `encryptFileChunk()` 来保证 IV/AAD/长度一致

并发/覆盖：
- 同一个分片如果已存在会被拒绝写入（避免并发覆盖导致数据损坏）；失败时临时文件会被清理

#### 2.5) 查询上传状态（断点续传）

`GET /api/pastes/{paste_id}/files/{upload_id}/status`

返回：
- `uploaded_chunks[]`：已上传分片索引列表（升序）
- `next_index`：建议继续上传的下一个分片索引（若已齐全则等于 `total_chunks`）

前端实现（Web）：
- 上传失败后点击“重试”会优先复用旧 `upload_id` 调用 status，跳过已上传分片继续上传；若会话过期/不匹配则回退到重新 `init`
- 多文件同时上传默认并发为 `10`，超出会排队（可在 `web/src/services/config.ts` 的 `DEFAULT_UPLOAD_CONCURRENCY` 调整）

#### 3) 完成上传（complete）

`POST /api/pastes/{paste_id}/files/{upload_id}/complete`

可选校验：
- `checksum_sha256`：整文件明文 SHA256（仅 `server` 模式可由服务端重算校验）
- `chunk_hashes_sha256[]`：每片 SHA256（`server` 模式对“明文分片”，`client` 模式对“加密分片”）

落盘：
- 会写入 `data/files/{paste_id}/{file_id}.manifest.json`，用于下载时按分片边界进行流式解密与 AAD 校验

#### 4) 下载解密（chunked 文件）

`GET /api/pastes/{paste_id}/files/{file_id}?encryption_key=...`

若存在 manifest，服务端会按分片边界读取并使用 AAD 进行流式解密（`aad_required=true` 时不会降级为无 AAD 解密）。

### 前端文件判重（仅 UI 级）

当前后端不会做“重复上传”拦截；为了减少误操作与带宽浪费，前端在**同一页面会话**内做了一层判重：如果检测到重复，会**直接跳过该文件，不发起上传**，并通过 `snackbar` 提示。

实现位置：`web/src/components/upload/FileUploader.vue`（`processFiles()` / `computeDedupeFingerprint()`）。

#### 判重范围

判重仅在当前浏览器页面/Tab 的内存状态中生效，覆盖三类列表：
- 上传中（`uploadingFiles`）
- 上传失败（`failedFiles`）
- 已上传（`uploadedFiles`）

同时也会对“同一次选择/拖拽/粘贴”这一批文件内部做去重。

#### 指纹算法（fingerprint）

判重依赖“指纹字符串”一致（而非文件名一致）。指纹的选择逻辑：

- **优先使用内容哈希**：`sha256:<hex>`
  - 条件：`0 < file.size <= 20MB` 且（来源是粘贴 `source=paste` **或**文件看起来是图片）
  - “看起来是图片”的判断：`file.type` 以 `image/` 开头，或扩展名属于 `png/jpg/jpeg/gif/webp/bmp/svg/ico/tiff/avif`
  - 目的：让“Ctrl+V 粘贴的图片”和“拖拽/选择的同一张图片”可以跨来源判重

- **粘贴的兜底指纹**：`paste:<name>::<size>::<type>`
  - 原因：剪贴板生成的 `File.lastModified` 经常变化，用它会导致同内容反复粘贴不命中

- **选择/拖拽的元信息指纹**：`file:<name>::<size>::<lastModified>`
  - 适用于非图片或超过 20MB 的文件（避免对大文件做全量 hash 带来内存/耗时问题）

#### 行为细节

- `processFiles()` 会先构建已存在指纹集合，然后为待上传文件逐个计算指纹：
  - 若“本批次已见过”或“会话内已存在”，该文件加入 `skippedFiles` 并跳过
  - 否则加入 `dedupedFiles` 并继续上传
- `startUpload()` 会把指纹跟随上传状态保存到 `uploading/failed/uploaded`，保证后续不同来源的文件也能命中判重

#### 已知限制

- 这是**体验级**判重：不会阻止后端接受重复内容（如果你绕过前端/换浏览器/刷新页面，仍可重复上传）。
- 非图片且 >20MB 的文件默认不算内容哈希，可能出现“内容相同但指纹不同”的漏判（例如复制文件导致 `lastModified` 不同）。

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
