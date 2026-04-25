# 创建 Paste

本文介绍如何通过 API 创建并发布 Paste。

创建成功后，服务端会返回 `admin_key`，后续写入、发布、更新和删除都使用这个 Paste 专用管理密钥。

如果还需要上传图片、附件或大文件，请参阅 [Paste 文件上传](/docs/paste-files)。

---

## 流程概览

创建并发布一个纯文本 Paste 通常需要 3 步：

```text
POST /api/pastes                          创建草稿
POST /api/pastes/{paste_id}/content       写入内容
POST /api/pastes/{paste_id}/publish       发布
```

第 1 步返回的 `admin_key` 是后续管理该 Paste 的凭据：

```http
X-Paste-Admin-Key: your_admin_key
```

---

## 核心概念

### paste_id

Paste 的唯一标识，后续接口都需要使用。

### admin_key

用于管理单个 Paste 的密钥。

- 由 `POST /api/pastes` 返回
- 丢失后无法再修改、删除或发布该 Paste

### encryption_mode

创建 Paste 时必须指定加密模式：

| 模式 | 适用场景 | 内容写入方式 |
|------|----------|-------------|
| `server` | 脚本、后端服务、自动化任务 | 发送明文 `content`，服务端负责加密保存 |
| `client` | 需要兼容 Web 编辑器的客户端 | 发送客户端加密后的 `encrypted_content` |

首次接入建议使用 `server` 模式。

---

## 快速开始：server 模式

以下示例使用 `{BASE_URL}` 表示你的 Material Bin 服务地址。

### 第 1 步：创建草稿

```bash
curl -X POST '{BASE_URL}/api/pastes' \
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
  "expires_at": "2026-05-01T12:34:56Z",
  "max_total_upload_size": 1073741824,
  "remaining_upload_size": 1073741824,
  "timestamp": 1777600000
}
```

请保存 `paste_id` 和 `admin_key`。

### 第 2 步：写入内容

```bash
curl -X POST '{BASE_URL}/api/pastes/Ab3kL9xQ/content' \
  -H 'Content-Type: application/json' \
  -H 'X-Paste-Admin-Key: your_admin_key' \
  -d '{
    "content": "Hello Material Bin\nThis paste was created by API."
  }'
```

返回示例：

```json
{
  "message": "内容更新成功",
  "timestamp": 1777600001
}
```

### 第 3 步：发布

```bash
curl -X POST '{BASE_URL}/api/pastes/Ab3kL9xQ/publish' \
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
  "encryption_key": "your_encryption_key",
  "timestamp": 1777600002
}
```

`server` 模式发布成功后会返回 `encryption_key`。请保存它：发布后继续修改内容、上传文件或读取明文时会用到。

---

## client 模式

`client` 模式用于实现与 Web 编辑器兼容的客户端。调用流程与 `server` 模式相同，但内容需要由客户端加密后再发送：

```json
{
  "encrypted_content": "base64_encrypted_content"
}
```

如果你只是用脚本或后端服务创建 Paste，通常不需要使用 `client` 模式。

---

## 接口说明

### `POST /api/pastes`

创建草稿 Paste。

**认证：** 不需要

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `encryption_mode` | string | 是 | `server` 或 `client` |

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `paste_id` | string | Paste ID |
| `admin_key` | string | Paste 管理密钥 |
| `expires_at` | string | 草稿过期时间 |
| `max_total_upload_size` | integer | 单个 Paste 的文件总容量上限，字节。`0` 表示不限制 |
| `remaining_upload_size` | integer 或 null | 剩余可上传容量 |
| `timestamp` | integer | 响应时间戳 |

草稿默认 24 小时后过期。

---

### `POST /api/pastes/{paste_id}/content`

写入或更新 Paste 内容。

**认证：** 需要 `X-Paste-Admin-Key`

```http
X-Paste-Admin-Key: your_admin_key
```

如果 Paste 已发布且使用 `server` 模式，还需要：

```http
X-Encryption-Key: your_encryption_key
```

**请求体：**

| 字段 | 适用模式 | 说明 |
|------|----------|------|
| `content` | `server` | 明文内容 |
| `encrypted_content` | `client` | 加密后的内容 |

请求体字段必须与创建时的 `encryption_mode` 匹配。

---

### `POST /api/pastes/{paste_id}/publish`

发布草稿 Paste。

**认证：** 需要 `X-Paste-Admin-Key`

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

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 标题，最长 255 字符，不能为空 |
| `type` | string | 否 | `txt` 或 `md`，默认 `txt` |
| `expire_time` | string | 是 | `7d`、`30d`、`1y` 或 `never` |
| `max_views` | integer | 是 | 最大查看次数。`-1` 表示不限制，`1` 表示阅后即焚 |
| `access_key` | string | 否 | 访问密码，最长 72 字节 |

发布前必须已经写入内容，且 Paste 仍处于草稿状态。

---

## Markdown Paste 示例

发布 Markdown 内容时，将 `type` 设置为 `md`：

```bash
curl -X POST '{BASE_URL}/api/pastes/Ab3kL9xQ/publish' \
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

写入内容时发送 Markdown 文本：

```markdown
# Hello

This is a markdown paste.
```

---

## 常见问题

### 创建草稿失败

检查 `Content-Type` 是否为 `application/json`，以及 `encryption_mode` 是否为 `server` 或 `client`。

### 写入内容返回 401

通常是缺少 `X-Paste-Admin-Key`。

### 写入内容返回 403

可能是 `admin_key` 错误，或发布后的 `server` 模式 Paste 缺少 `X-Encryption-Key`。

### 发布失败，提示内容为空

请先成功调用 `POST /api/pastes/{paste_id}/content` 写入内容。

### 想先验证流程

优先使用 `server` 模式。它不需要你自己实现内容加密。
