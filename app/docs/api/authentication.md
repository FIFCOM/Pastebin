# 认证与凭据

本文说明本 API 文档中会出现的几类凭据。它们用途不同，不能互换。

---

## 用户 API Key

用户 API Key 通过 `Authorization` 请求头传递：

```http
Authorization: Bearer pk_your_api_key
```

当前用户 API Key 只会在以下接口中被读取，且都是**可选**的：

| 接口 | API Key 的作用 |
|------|----------------|
| `POST /api/rooms/member-token` | 生成协作成员令牌时使用用户身份作为显示名来源 |
| `POST /api/rooms/member-token/refresh` | 刷新成员令牌时同步用户显示名 |

不传 API Key 时，这两个接口仍可匿名调用，显示名会使用 `Guest_xxxxx` 格式。

> API Key 通常以 `pk_` 开头。API Key 的创建、删除和列表管理不在本文档范围内。

---

## 账户密码重置

忘记密码流程使用邮箱验证码确认邮箱归属，然后写入新密码。由于 Material Bin 使用用户密码派生密钥来保护用户密钥，忘记密码时服务端无法恢复旧用户密钥。

因此，通过找回密码重置成功后：

- 系统会生成新的用户密钥。
- 旧会话会被撤销，需要使用新密码重新登录。
- 用户保存的历史记录和收藏关联会被清空，因为这些关联中保存的 Paste 解密密钥和管理密钥由旧用户密钥加密。
- Paste 本体不会被删除。仍持有 Paste 链接、访问密码、`admin_key` 或 `encryption_key` 的用户，可以继续按原有凭据访问或管理对应 Paste。
- 用户 API Key 不会因密码重置自动撤销。需要轮换 API Key 时，请登录后在 API Key 管理页面手动删除并重新创建。

已登录用户修改密码属于不同流程：系统会先用当前密码恢复旧用户密钥，再用新密码重新加密同一个用户密钥，因此不会清空历史记录和收藏关联。

公开邮箱验证码接口会对注册和找回密码返回统一提示，并在后台发送真实验证码，避免通过响应内容或请求耗时暴露邮箱是否存在。验证码重发间隔由系统的邮箱验证码策略配置决定。

---

## 公开接口

公开接口不需要 `Authorization` 请求头。

本文档中的公开接口包括：

- `POST /api/pastes`
- `GET /api/config`

部分公开入口会返回专用凭据供后续流程使用，例如 `POST /api/pastes` 返回 `admin_key`，Paste 写入接口随后使用 `X-Paste-Admin-Key`。

---

## Paste 管理密钥

Paste 管理密钥是 `POST /api/pastes` 创建草稿时返回的 `admin_key`。它只管理对应 Paste，不代表用户身份。

```http
X-Paste-Admin-Key: your_admin_key
```

需要 `X-Paste-Admin-Key` 的接口包括：

- `POST /api/pastes/{paste_id}/content`
- `POST /api/pastes/{paste_id}/files/init`
- `GET /api/pastes/{paste_id}/files/{upload_id}/status`
- `PUT /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}`
- `POST /api/pastes/{paste_id}/files/{upload_id}/complete`
- `POST /api/pastes/{paste_id}/files/{upload_id}/abort`
- `DELETE /api/pastes/{paste_id}/files/{file_id}`
- `POST /api/pastes/{paste_id}/publish`
- `PUT /api/pastes/{paste_id}`
- `DELETE /api/pastes/{paste_id}`

草稿 Paste 的读取也需要 `X-Paste-Admin-Key`。已发布且未设置访问密码的 Paste 可以公开读取。

---

## Paste 访问密码

发布 Paste 时可以设置 `access_key`。设置后，公开读取接口需要通过查询参数传递访问密码：

```http
GET /api/pastes/{paste_id}/content?access_key=your_password
```

`access_key` 只控制能否访问 Paste，不用于解密内容。

---

## Paste 加密密钥

`server` 模式发布成功后会返回 `encryption_key`。它用于解密内容和文件，也用于在发布后继续写入 `server` 模式内容或文件。

读取时作为查询参数传递：

```http
GET /api/pastes/{paste_id}/content?encryption_key=your_encryption_key
```

发布后继续写入 `server` 模式 Paste 时作为请求头传递：

```http
X-Encryption-Key: your_encryption_key
```

请妥善保存 `admin_key` 和 `encryption_key`。丢失后，服务端无法重新展示完整明文。
