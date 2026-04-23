# 协作成员令牌

本节覆盖协作模块中**唯一支持可选 API Key 识别**的两个接口。

> 其余协作 HTTP 接口（创建房间、加入房间、成员列表、分享 Paste 等）通过 `X-Member-Token` 传递 `member_token`，**不支持**用户 API Key（`pk_...`）。WebSocket 仍按实时协议在连接后提交 `member_token`。

---

## 可选认证说明

以下两个接口依赖 `get_optional_user`，这意味着：

- **不登录也可以调用**：不传 `Authorization` 头即可匿名获取
- **带了 API Key 也可以**：如果传了 `Authorization: Bearer pk_{api_key}`，系统会识别你的用户身份
- **区别在于显示名**：登录用户使用真实用户名，匿名用户使用 `Guest_xxxxx` 格式的随机名

---

## 获取成员令牌

### `POST /api/rooms/member-token`

获取一个协作房间成员令牌（Member Token），用于后续加入协作房间。

| 参数 | 说明 |
|------|------|
| `Authorization` | **可选**，`Bearer {access_token}` 或 `Bearer pk_{api_key}` |

**不需要请求体**。

**响应**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `member_token` | string | JWT 格式的成员令牌，有效期 24 小时 |
| `display_name` | string | 显示名（登录用户为真实用户名，匿名用户为 Guest_xxxxx） |

**用途**：获取 `member_token` 后，你可以用它来：

1. 创建协作房间
2. 加入已有房间
3. 查看成员列表
4. 分享 Paste 到房间
5. 建立 WebSocket 实时连接

---

## 刷新成员令牌

### `POST /api/rooms/member-token/refresh`

刷新当前成员令牌的显示名。

| 参数 | 说明 |
|------|------|
| `Authorization` | **可选**，`Bearer {access_token}` 或 `Bearer pk_{api_key}` |
| `X-Member-Token` | 必需，请求头，传入现有的 member_token |

**用途**：当用户从匿名状态变为登录状态时，调用此接口可将 `Guest_xxxxx` 更新为真实用户名。

**响应**：返回新的 `member_token` 和更新后的 `display_name`。

**可能的错误**：

| 状态码 | 说明 |
|--------|------|
| 401 | 缺少 `X-Member-Token` 头 |
| 400 | `X-Member-Token` 无效 |

---

## 不支持 API Key 的协作接口

以下协作 HTTP 接口仅支持通过 `X-Member-Token` 传递 `member_token`，不接受用户 API Key：

| 接口 | 认证方式 |
|------|----------|
| `POST /api/rooms` — 创建房间 | `X-Member-Token` |
| `GET /api/join/{pin_code}` — 获取房间信息 | 无需认证 |
| `POST /api/rooms/{room_id}/join` — 加入房间 | `X-Member-Token` |
| `GET /api/rooms/{room_id}/members` — 成员列表 | `X-Member-Token` |
| `POST /api/rooms/{room_id}/pastes` — 分享 Paste | `X-Member-Token` |
| `GET /api/rooms/{room_id}/pastes` — 房间 Paste 列表 | `X-Member-Token` |
| `DELETE /api/rooms/{room_id}/leave` — 离开房间 | `X-Member-Token` |
| `WS /api/rooms/{room_id}/ws` — 实时 WebSocket | 连接后按实时协议提交 `member_token` |
