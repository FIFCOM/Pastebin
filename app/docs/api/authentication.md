# 认证

本文介绍如何通过 API Key 或 `access_token` 访问需要身份验证的接口。

当前统一用户接口已经收敛为仅支持 `access_token`。API Key 只会在少数“可选识别用户身份”的场景中被读取，不再作为账户管理接口的正式认证方式。

---

## 快速上手

1. 登录 Material Bin，进入 `/users?tab=apikeys` 页面
2. 创建一个新的 API Key，保存好返回的密钥明文
3. 在请求头中携带 API Key：

```http
Authorization: Bearer {api_key}
```

```bash
curl -X POST \
  -H "Authorization: Bearer pk_your_api_key" \
  http://localhost:8000/api/rooms/member-token
```

> API Key 通常以 `pk_` 开头。密钥明文只在创建时显示一次，丢失后只能删除重建。

---

## 创建与管理

### 通过页面创建

1. 在浏览器中登录 Material Bin
2. 进入 `/users?tab=apikeys` 页面
3. 点击创建，填写名称和过期时间
4. 立即保存返回的密钥明文

> 密钥明文只在创建时返回一次。之后你可以查看 Key 列表，但无法再获取完整明文。如果丢失，请删除旧 Key 并创建新的。

### 管理接口

| 接口 | 说明 |
|------|------|
| `GET /api/user/apikeys` | 查看自己的 API Key 列表，仅支持 `access_token` |
| `POST /api/user/apikeys` | 创建新的 API Key，仅支持 `access_token` |
| `DELETE /api/user/apikeys/{key_id}` | 删除指定的 API Key，仅支持 `access_token` |
| `POST /api/user/apikeys/cleanup-expired` | 清理已过期的 API Key，仅支持 `access_token` |

---

## 如何传递 API Key

API Key 通过 `Authorization` 请求头传递，格式固定为：

```http
Authorization: Bearer {api_key}
```

请注意：

- 不要将 API Key 放在 URL 查询参数中
- 不要使用其他请求头名称
- 系统只从 `Authorization: Bearer ...` 中读取 API Key

---

## 当前会读取 API Key 的接口

| 模块 | 接口 | 说明 |
|------|------|------|
| 协作 | `POST /api/rooms/member-token` | 可选携带 API Key，用于识别当前用户并生成显示名 |
| 协作 | `POST /api/rooms/member-token/refresh` | 可选携带 API Key，用于刷新成员显示名 |

## 仅支持 access_token 的接口

| 模块 | 接口 | 说明 |
|------|------|------|
| 用户信息 | `GET /api/users/me` | 获取当前用户信息 |
| 用户信息 | `GET /api/users/{user_id}` | 获取指定用户信息（普通用户只能查看自己） |
| 用户信息 | `PUT /api/users/{user_id}` | 更新自己的用户信息 |
| 用户信息 | `DELETE /api/users/{user_id}` | 删除自己的账户 |
| 用户管理 | `GET /api/users` | 获取用户列表（管理员） |
| 用户管理 | `POST /api/users` | 创建用户（管理员） |
| 会话管理 | `POST /api/users/logout-all` | 撤销当前用户的所有登录会话 |
| 会话管理 | `DELETE /api/users/sessions/{session_id}` | 撤销指定会话 |
| 会话管理 | `POST /api/users/cleanup-sessions` | 清理过期会话（管理员） |
| 两步验证 | `GET /api/users/me/totp` | 查看 TOTP 状态 |
| 两步验证 | `POST /api/users/me/totp` | 生成 TOTP 设置信息 |
| 两步验证 | `POST /api/users/me/totp/verify` | 验证并启用 TOTP |
| 两步验证 | `DELETE /api/users/me/totp` | 禁用 TOTP |
| 密钥管理 | `GET /api/user/apikeys` | 查看 API Key 列表 |
| 密钥管理 | `POST /api/user/apikeys` | 创建新的 API Key |
| 密钥管理 | `DELETE /api/user/apikeys/{key_id}` | 删除 API Key |
| 密钥管理 | `POST /api/user/apikeys/cleanup-expired` | 清理已过期的 API Key |
