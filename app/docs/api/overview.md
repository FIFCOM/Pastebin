# API 文档

本文档面向需要通过程序调用 Material Bin 接口的开发者，覆盖以下接口：

- **公开接口**：例如创建 Paste、读取公开 Paste、查询公开配置
- **API Key 可选识别接口**：可选使用 `Authorization: Bearer pk_...` 识别用户身份
- **Paste 管理接口**：使用创建 Paste 时返回的 `admin_key` 管理内容、文件和发布状态

不覆盖用户账户类接口、仅支持 `access_token` 的接口、用户 History、内部任务接口。

---

## 文档结构

| 模块 | 内容 |
|------|------|
| [认证与凭据](/docs/authentication) | API Key、Paste 管理密钥、访问密码、加密密钥的区别 |
| [创建 Paste](/docs/paste-creation) | 创建、写入并发布 Paste |
| [Paste 文件上传](/docs/paste-files) | 内容、文件、读取与下载接口 |
| [API Key 可用接口](/docs/api-keys) | 当前会读取用户 API Key 的接口 |
| [协作公开接口](/docs/collaboration) | 获取成员令牌、刷新成员令牌、查询加入信息 |

---

## 凭据速览

| 凭据 | 传递方式 | 用途 |
|------|----------|------|
| 用户 API Key | `Authorization: Bearer pk_...` | 仅在少数协作令牌接口中可选使用，用于识别显示名 |
| Paste 管理密钥 | `X-Paste-Admin-Key: ...` | 管理某个 Paste 的内容、文件和发布状态 |
| Paste 访问密码 | `?access_key=...` | 访问设置了密码的已发布 Paste |
| Paste 加密密钥 | `?encryption_key=...` 或 `X-Encryption-Key: ...` | 解密或继续写入 server 模式 Paste |

用户 API Key 和 Paste 管理密钥不是同一种凭据，不能互换。

---

## 覆盖的接口

### API Key 可选识别

| 接口 | 说明 |
|------|------|
| `POST /api/rooms/member-token` | 获取协作成员令牌，可选使用 API Key 生成用户显示名 |
| `POST /api/rooms/member-token/refresh` | 刷新协作成员令牌，可选使用 API Key 同步用户显示名 |

### 公开系统入口

| 接口 | 说明 |
|------|------|
| `GET /api/config` | 获取公开配置 |
| `GET /api/docs`、`GET /api/docs/{slug}` | 获取本文档 Markdown |

### Paste 接口

创建草稿后，后续写入、上传、发布、更新、删除使用创建时返回的 `admin_key`。

| 接口 | 说明 |
|------|------|
| `POST /api/pastes` | 创建草稿 |
| `POST /api/pastes/{paste_id}/content` | 写入或更新内容 |
| `POST /api/pastes/{paste_id}/files/init` | 初始化文件上传 |
| `GET /api/pastes/{paste_id}/files/{upload_id}/status` | 查询上传状态 |
| `PUT /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}` | 上传分片 |
| `POST /api/pastes/{paste_id}/files/{upload_id}/complete` | 完成上传 |
| `POST /api/pastes/{paste_id}/files/{upload_id}/abort` | 取消上传 |
| `DELETE /api/pastes/{paste_id}/files/{file_id}` | 删除文件 |
| `POST /api/pastes/{paste_id}/publish` | 发布 Paste |
| `GET /api/pastes/{paste_id}` | 获取 Paste 信息 |
| `GET /api/pastes/{paste_id}/content` | 获取 Paste 内容和文件列表 |
| `GET /api/pastes/{paste_id}/files/{file_id}/manifest` | 获取文件 manifest |
| `GET /api/pastes/{paste_id}/files/{file_id}/meta` | 获取文件元信息 |
| `GET /api/pastes/{paste_id}/files/{file_id}` | 下载文件 |
| `PUT /api/pastes/{paste_id}` | 更新 Paste 设置 |
| `DELETE /api/pastes/{paste_id}` | 删除 Paste |
