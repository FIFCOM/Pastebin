# API Key 可用接口

当前 Material Bin 的用户 API Key 只在协作成员令牌接口中作为**可选身份识别**使用。

API Key 通过 `Authorization` 请求头传递：

```http
Authorization: Bearer pk_your_api_key
```

不传 API Key 时，这些接口仍可匿名调用。

---

## 获取成员令牌

### `POST /api/rooms/member-token`

获取协作房间成员令牌。

**认证：** 可选 API Key

| 请求头 | 必填 | 说明 |
|--------|------|------|
| `Authorization` | 否 | `Bearer pk_your_api_key` |

**请求体：** 不需要

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `member_token` | string | 协作成员令牌，有效期 24 小时 |
| `display_name` | string | 显示名。传入有效 API Key 时使用用户显示名，否则为 `Guest_xxxxx` |

**示例：**

```bash
curl -X POST https://example.com/api/rooms/member-token \
  -H 'Authorization: Bearer pk_your_api_key'
```

匿名调用：

```bash
curl -X POST https://example.com/api/rooms/member-token
```

---

## 刷新成员令牌

### `POST /api/rooms/member-token/refresh`

刷新已有成员令牌，并在传入有效 API Key 时同步用户显示名。

**认证：** 可选 API Key

| 请求头 | 必填 | 说明 |
|--------|------|------|
| `X-Member-Token` | 是 | 当前已有的 `member_token` |
| `Authorization` | 否 | `Bearer pk_your_api_key` |

**请求体：** 不需要

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `member_token` | string | 新的成员令牌 |
| `display_name` | string | 更新后的显示名 |

**示例：**

```bash
curl -X POST https://example.com/api/rooms/member-token/refresh \
  -H 'X-Member-Token: your_member_token' \
  -H 'Authorization: Bearer pk_your_api_key'
```