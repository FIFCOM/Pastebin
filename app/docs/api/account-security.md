# 账户与安全

本节覆盖账户管理相关接口。当前本页所有接口都仅支持 `access_token`，不再接受 API Key（`pk_...`）。

> 如无特殊说明，统一通过 `Authorization: Bearer {access_token}` 传递用户登录态。

## 当前用户信息

### `GET /api/users/me`

获取当前用户信息。

| 参数 | 说明 |
|------|------|
| `Authorization` | `Bearer {access_token}` |

**响应**：返回用户对象，包含 `id`、`username`、`email`、`role`、`is_active` 等字段。

**可能的错误**：

| 状态码 | 说明 |
|--------|------|
| 401 | 认证失败（Token 无效） |
| 401 | 账户已被禁用 |

---

## 获取用户信息

### `GET /api/users/{user_id}`

根据用户 ID 获取用户信息。

| 参数 | 说明 |
|------|------|
| `user_id` | 路径参数，用户 ID |
| `Authorization` | `Bearer {access_token}` |

**权限说明**：

- **普通用户**：只能查看自己的信息（`user_id` 必须等于当前用户 ID）
- **管理员**：可以查看任意用户的信息

**可能的错误**：

| 状态码 | 说明 |
|--------|------|
| 403 | 无权限查看其他用户 |
| 404 | 用户不存在 |

---

## 更新用户信息

### `PUT /api/users/{user_id}`

更新用户信息。

| 参数 | 说明 |
|------|------|
| `user_id` | 路径参数 |
| `Authorization` | `Bearer {access_token}` |

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | 否 | 新用户名 |
| `email` | string | 否 | 新邮箱 |
| `password` | string | 否 | SHA256 哈希后的新密码 |
| `current_password` | string | 条件 | 修改邮箱或密码时必需，用于验证身份 |
| `role` | string | 否 | 用户角色（仅管理员可修改） |
| `is_active` | boolean | 否 | 是否启用（仅管理员可修改） |

**权限说明**：

- **普通用户**：只能更新自己的信息，修改邮箱或密码时需提供当前密码
- **管理员**：可更新任意用户的所有信息

---

## 删除用户

### `DELETE /api/users/{user_id}`

删除用户。

| 参数 | 说明 |
|------|------|
| `user_id` | 路径参数 |
| `Authorization` | `Bearer {access_token}` |

**权限说明**：

- **普通用户**：只能删除自己的账户
- **管理员**：可删除任意用户

---

## 会话管理

### `DELETE /api/users/sessions/{session_id}` — 撤销会话

撤销指定会话。

| 参数 | 说明 |
|------|------|
| `session_id` | 路径参数，会话 ID |
| `Authorization` | `Bearer {access_token}` |

用户只能撤销自己的会话。撤销后该 session 的 refresh token 失效。

**可能的错误**：

| 状态码 | 说明 |
|--------|------|
| 404 | 会话不存在或无权限 |

### `POST /api/users/logout-all` — 全部设备登出

撤销当前用户的所有会话。

| 参数 | 说明 |
|------|------|
| `Authorization` | `Bearer {access_token}` |

**响应**：`MessageResponse`，包含撤销的会话数量。

## TOTP 两步验证

以下四个接口用于管理 TOTP（基于时间的一次性密码）两步验证。

### `GET /api/users/me/totp` — 查看 TOTP 状态

查询当前用户是否已启用 TOTP。

| 参数 | 说明 |
|------|------|
| `Authorization` | `Bearer {access_token}` |

**响应**：返回 `is_enabled` 状态。

### `POST /api/users/me/totp` — 初始化 TOTP 设置

生成 TOTP 密钥和 provisioning URI。

| 参数 | 说明 |
|------|------|
| `Authorization` | `Bearer {access_token}` |

**响应**：返回 `secret`（密钥）和 `uri`（可用于生成二维码的 provisioning URI）。

> 前端收到后应展示二维码，让用户用验证器 App 扫码。

### `POST /api/users/me/totp/verify` — 验证并启用 TOTP

用户输入验证器 App 中的 6 位验证码后调用，验证成功则启用两步验证。

| 参数 | 说明 |
|------|------|
| `Authorization` | `Bearer {access_token}` |

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `totp_code` | string | 是 | 6 位 TOTP 验证码 |

**响应**：`MessageResponse`，`message: "TOTP验证成功，两步验证已启用"`。

### `DELETE /api/users/me/totp` — 禁用 TOTP

关闭两步验证。

| 参数 | 说明 |
|------|------|
| `Authorization` | `Bearer {access_token}` |

---

## API Key 支持说明

以下账户相关接口都**不支持** API Key 调用：

| 接口 | 原因 |
|------|------|
| `POST /api/users/logout-all` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `GET /api/users/me` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `GET /api/users/{user_id}` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `PUT /api/users/{user_id}` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `DELETE /api/users/{user_id}` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `GET /api/users` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `POST /api/users` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `GET /api/users/{user_id}/sessions` | 依赖 `get_current_user_and_session`，需要当前 session |
| `DELETE /api/users/{user_id}/sessions/others` | 依赖 `get_current_user_and_session`，需要保留当前 session |
| `DELETE /api/users/sessions/{session_id}` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `POST /api/users/cleanup-sessions` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `GET /api/users/me/totp` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `POST /api/users/me/totp` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `POST /api/users/me/totp/verify` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `DELETE /api/users/me/totp` | 依赖 `get_current_user_by_access_token`，仅接受 `access_token` |
| `POST /api/users/register` | 注册接口，无需认证 |
| `POST /api/users/login` | 登录接口，无需认证 |
| `POST /api/users/login-totp` | TOTP 登录接口，无需认证 |
| `POST /api/users/refresh` | 刷新 Token，使用 Cookie 中的 refresh token |
| `POST /api/users/logout` | 登出，使用 Cookie 中的 refresh token |
