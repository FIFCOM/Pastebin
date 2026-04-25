# 协作公开接口

本页介绍协作成员令牌和加入信息查询接口。

协作模块中的房间创建、加入、成员列表、分享 Paste、离开房间和 WebSocket 实时连接需要 `X-Member-Token`，不在本文档展开。

---

## 获取成员令牌

### `POST /api/rooms/member-token`

获取协作成员令牌，用于后续协作流程。

**认证：** 不需要。可选携带用户 API Key。

| 请求头 | 必填 | 说明 |
|--------|------|------|
| `Authorization` | 否 | `Bearer pk_your_api_key` |

**请求体：** 不需要

**行为说明：**

- 不传 `Authorization` 时，返回匿名成员令牌
- 传入有效 API Key 时，返回与用户身份关联的成员令牌
- API Key 只影响显示名，不授予房间管理权限

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `member_token` | string | 成员令牌，有效期 24 小时 |
| `display_name` | string | 成员显示名 |

---

## 刷新成员令牌

### `POST /api/rooms/member-token/refresh`

刷新已有成员令牌。常见场景是匿名成员绑定身份后，将显示名同步为用户显示名。

**认证：** 需要 `X-Member-Token`。可选携带用户 API Key。

| 请求头 | 必填 | 说明 |
|--------|------|------|
| `X-Member-Token` | 是 | 当前已有的成员令牌 |
| `Authorization` | 否 | `Bearer pk_your_api_key` |

**请求体：** 不需要

**响应字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `member_token` | string | 新的成员令牌 |
| `display_name` | string | 更新后的显示名 |

**可能的错误：**

| 状态码 | 说明 |
|--------|------|
| 401 | 缺少 `X-Member-Token` |
| 400 | `X-Member-Token` 无效 |

---

## 查询加入信息

### `GET /api/join/{pin_code}`

通过 6 位房间 PIN 查询房间加入信息。

**认证：** 不需要

| 参数 | 位置 | 必填 | 说明 |
|------|------|------|------|
| `pin_code` | 路径 | 是 | 6 位字母数字 PIN |

该接口只用于展示加入房间前的信息，不需要 API Key。
