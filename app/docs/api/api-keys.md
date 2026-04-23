# API Key 管理

本节覆盖 API Key 的自管理接口。这些接口仅接受 `access_token`，不再支持 `Authorization: Bearer pk_{api_key}`。

> **注意**：你必须先通过登录拿到 `access_token`，再管理自己的 API Key。

---

## 列出 API Key

### `GET /api/user/apikeys`

获取当前用户的所有 API Key 列表。

| 参数 | 说明 |
|------|------|
| `Authorization` | `Bearer {access_token}` |

**响应**：返回 API Key 列表，**不包含密钥明文**。每条记录包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | integer | Key ID |
| `name` | string | 名称 |
| `is_active` | boolean | 是否有效 |
| `expires_at` | string | 过期时间（可为 null） |
| `last_used_at` | string | 最后使用时间 |
| `created_at` | string | 创建时间 |

---

## 创建 API Key

### `POST /api/user/apikeys`

创建新的 API Key。

| 参数 | 说明 |
|------|------|
| `Authorization` | `Bearer {access_token}` |

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 否 | API Key 名称（用于标识） |

**响应**：返回新创建的 API Key 信息，**包含密钥明文（`key` 字段）**。

> **重要**：密钥明文**仅在创建时返回一次**，之后无法查看。请妥善保存。

---

## 删除 API Key

### `DELETE /api/user/apikeys/{key_id}`

删除指定的 API Key。

| 参数 | 说明 |
|------|------|
| `key_id` | 路径参数，Key ID |
| `Authorization` | `Bearer {access_token}` |

用户只能删除自己的 API Key。

> 注意：删除某个 API Key 后，后续也无法再用于那些会可选识别用户身份的接口。

**可能的错误**：

| 状态码 | 说明 |
|--------|------|
| 404 | API Key 不存在或无权限删除 |

---

## 清理过期 API Key

### `POST /api/user/apikeys/cleanup-expired`

清理当前用户已过期的 API Key。

| 参数 | 说明 |
|------|------|
| `Authorization` | `Bearer {access_token}` |

**响应**：`MessageResponse`，包含清理的数量。

---

## 权限边界说明

- API Key 自管理接口只接受 `access_token`
- 普通用户的 API Key 不具备额外的后台管理权限
- 管理员的 API Key 也不能再调用账户管理接口
- API Key 当前只会在少数“可选识别用户身份”的接口中被读取
