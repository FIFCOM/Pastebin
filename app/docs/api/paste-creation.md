# 创建 Paste

本文介绍如何通过 API 创建并发布一个 Paste。

如果你只需要创建纯文本 Paste，按本文操作即可。如果还需要上传图片、附件或大文件，请参阅 [Paste 文件上传](/docs/pastes-files)。

> 认证相关内容请参阅 [认证说明](/docs/authentication)。

---

## 概述

创建一个 Paste 需要依次调用 3 个接口：

```text
POST /api/pastes                          ← 创建草稿
POST /api/pastes/{paste_id}/content       ← 写入内容
POST /api/pastes/{paste_id}/publish       ← 发布
```

其中，第 1 步是公开接口，无需登录或 API Key。第 1 步返回的 `admin_key` 是后续所有操作的管理凭据，需要通过请求头传递：

```http
X-Paste-Admin-Key: {admin_key}
```

---

## 核心概念

### paste_id

Paste 的唯一标识，后续所有接口都需要用到。

### admin_key

用于管理该 Paste 的密钥。

- 由 `POST /api/pastes` 返回
- 与用户登录 Token 和 API Key 无关
- 一旦丢失，将无法再对该 Paste 进行任何修改

### encryption_mode（加密模式）

创建 Paste 时必须指定加密模式，可选值如下：

| 模式 | 适用场景 | 内容写入方式 |
|------|----------|-------------|
| `server` | 脚本、后端服务等需要快速接入的场景 | 直接发送明文 `content` |
| `client` | 需要与 Web 编辑器保持一致的客户端 | 发送加密后的 Base64 字符串 `encrypted_content` |

如果是首次接入，**建议使用 `server` 模式**，无需额外实现加密逻辑。

---

## 快速开始（server 模式）

以下示例使用 `server` 模式演示完整的创建流程。

### 第 1 步：创建草稿

```bash
curl -X POST http://localhost:8000/api/pastes \
  -H 'Content-Type: application/json' \
  -d '{
    "encryption_mode": "server"
  }'
```

返回示例：

```json
{
  "paste_id": "Ab3kL9xQ",
  "admin_key": "your_admin_key",
  "expires_at": "2026-04-19T12:34:56Z",
  "max_total_upload_size": 104857600,
  "remaining_upload_size": 104857600,
  "timestamp": 1776500000
}
```

请保存好 `paste_id` 和 `admin_key`，后续步骤都会用到。

### 第 2 步：写入内容

```bash
curl -X POST http://localhost:8000/api/pastes/Ab3kL9xQ/content \
  -H 'Content-Type: application/json' \
  -H 'X-Paste-Admin-Key: your_admin_key' \
  -d '{
    "content": "Hello MaterialBin\nThis paste was created by API."
  }'
```

返回示例：

```json
{
  "message": "内容更新成功",
  "timestamp": 1776500001
}
```

### 第 3 步：发布

```bash
curl -X POST http://localhost:8000/api/pastes/Ab3kL9xQ/publish \
  -H 'Content-Type: application/json' \
  -H 'X-Paste-Admin-Key: your_admin_key' \
  -d '{
    "settings": {
      "title": "My First Paste",
      "type": "txt",
      "expire_time": "30d",
      "max_views": -1
    }
  }'
```

返回示例：

```json
{
  "paste_id": "Ab3kL9xQ",
  "admin_key": "your_admin_key",
  "encryption_key": "optional_server_key",
  "timestamp": 1776500002
}
```

> 使用 `server` 模式时，发布成功会返回 `encryption_key`。请务必保存——发布后服务端会清除临时密钥，后续修改内容或上传文件时可能需要用到它。

至此，一个完整的 Paste 就创建好了。

---

## client 模式说明

Web 编辑器默认使用 `client` 模式，流程如下：

1. 调用 `POST /api/pastes`，将 `encryption_mode` 设为 `client`
2. 在客户端将文本内容加密为 Base64 字符串
3. 调用 `POST /api/pastes/{paste_id}/content`，发送 `encrypted_content` 字段
4. 调用 `POST /api/pastes/{paste_id}/publish` 发布

如果你需要开发一个与 Web 编辑器完全兼容的第三方客户端，应当使用此模式。

---

## 接口详细说明

### POST /api/pastes

创建一个新的草稿 Paste。

**认证：** 不需要

**请求头：**

```http
Content-Type: application/json
```

**请求参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `encryption_mode` | string | 是 | `client` 或 `server` |

**返回字段：**

| 字段 | 说明 |
|------|------|
| `paste_id` | Paste 的唯一标识 |
| `admin_key` | 后续管理该 Paste 的凭据 |
| `expires_at` | 草稿过期时间 |
| `max_total_upload_size` | 总上传容量上限（字节） |
| `remaining_upload_size` | 剩余可用上传容量（字节） |
| `timestamp` | 响应时间戳 |

---

### POST /api/pastes/{paste_id}/content

写入或更新 Paste 的文本内容。

**认证：** 需要

```http
X-Paste-Admin-Key: {admin_key}
```

**请求参数（二选一）：**

| 字段 | 适用模式 | 说明 |
|------|----------|------|
| `content` | `server` | 明文内容 |
| `encrypted_content` | `client` | 加密后的 Base64 字符串 |

请求体中的字段必须与创建时指定的加密模式匹配：`server` 模式只接受 `content`，`client` 模式只接受 `encrypted_content`。

**补充说明：**

- 如果 Paste 已发布后再次更新内容，状态会变为 `edited`
- 在草稿阶段，`server` 模式下服务端会自动管理加密密钥，无需额外传递
- 如果 Paste 已发布且需要继续更新，需要通过请求头传递发布时返回的加密密钥：

  ```http
  X-Encryption-Key: {encryption_key}
  ```

---

### POST /api/pastes/{paste_id}/publish

将草稿发布为可访问的 Paste。

**认证：** 需要

```http
X-Paste-Admin-Key: {admin_key}
```

**请求体：**

```json
{
  "settings": {
    "title": "My First Paste",
    "type": "txt",
    "expire_time": "30d",
    "max_views": -1,
    "access_key": "optional-password"
  }
}
```

**settings 字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 标题，不能为空 |
| `type` | string | 是 | 内容类型：`txt` 或 `md` |
| `expire_time` | string | 是 | 过期时间：`7d`、`30d`、`1y` 或 `never` |
| `max_views` | integer | 是 | 最大查看次数。`-1` 为不限制，`1` 为阅后即焚，其他值须大于 0 |
| `access_key` | string | 否 | 访问密码，最长 72 字节 |

**发布前提条件：**

- Paste 必须已经写入过内容
- 标题不能为空
- 当前状态必须是 `draft`

---

## Markdown Paste 示例

如果你想发布一个 Markdown 格式的 Paste，只需将 `type` 设为 `md`：

```bash
curl -X POST http://localhost:8000/api/pastes/Ab3kL9xQ/publish \
  -H 'Content-Type: application/json' \
  -H 'X-Paste-Admin-Key: your_admin_key' \
  -d '{
    "settings": {
      "title": "Markdown Demo",
      "type": "md",
      "expire_time": "never",
      "max_views": -1
    }
  }'
```

写入的内容可以是标准 Markdown 语法：

```markdown
# Hello

This is a markdown paste.
```

---

## 常见问题

### 创建草稿失败

- 检查 `Content-Type` 是否为 `application/json`
- 检查 `encryption_mode` 是否为 `client` 或 `server`

### 写入内容返回 401

通常是缺少 `X-Paste-Admin-Key` 请求头。正确格式为：

```http
X-Paste-Admin-Key: {admin_key}
```

### 写入内容返回 403

可能原因：

- `admin_key` 不正确
- `server` 模式下缺少 `X-Encryption-Key`（已发布的 Paste）

### 发布失败，提示内容为空

说明尚未成功写入内容，请确认第 2 步是否执行成功，以及请求体字段是否正确。

### client 模式上传失败

可能原因：

- 传了 `content` 而非 `encrypted_content`
- `encrypted_content` 的加密格式不符合要求

如果只是想先验证流程，建议切换到 `server` 模式。

---

## 下一步

如果你还需要上传图片、附件、大文件分片或断点续传等功能，请继续阅读 [Paste 文件上传](/docs/pastes-files)。
