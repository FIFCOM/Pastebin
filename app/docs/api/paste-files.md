# Paste 内容与文件

本页介绍 Paste 内容、文件上传、读取和下载接口。

Paste 管理操作使用创建草稿时返回的 `admin_key`：

```http
X-Paste-Admin-Key: your_admin_key
```

读取已发布 Paste 时，若发布时设置了访问密码，则需要 `access_key` 查询参数。

---

## 目录

- [文件上传流程](#文件上传流程)
- [凭据说明](#凭据说明)
- [写入内容](#写入内容)
- [初始化文件上传](#初始化文件上传)
- [查询上传状态](#查询上传状态)
- [上传分片](#上传分片)
- [完成上传](#完成上传)
- [取消上传](#取消上传)
- [删除文件](#删除文件)
- [更新 Paste 设置](#更新-paste-设置)
- [删除 Paste](#删除-paste)
- [在 Markdown 中引用文件](#在-markdown-中引用文件)
- [读取 Paste 信息](#读取-paste-信息)
- [读取内容](#读取内容)
- [文件元信息](#文件元信息)
- [文件 Manifest](#文件-manifest)
- [下载文件](#下载文件)
- [常见问题](#常见问题)

---

## 文件上传流程

文件上传是独立于文本内容写入的流程：

```text
POST /api/pastes/{paste_id}/files/init                          初始化上传
GET  /api/pastes/{paste_id}/files/{upload_id}/status            查询进度
PUT  /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}     上传分片
POST /api/pastes/{paste_id}/files/{upload_id}/complete          完成上传
```

初始化时返回的 `upload_id` 就是最终的 `file_id`。文件上传完成后，可通过以下地址引用：

```text
/api/pastes/{paste_id}/files/{file_id}
```

建议先上传文件，再写入引用文件的 Markdown 内容，最后发布 Paste。

---

## 凭据说明

| 凭据 | 传递方式 | 用途 |
|------|----------|------|
| `admin_key` | `X-Paste-Admin-Key` | 管理草稿、写入内容、上传文件、发布、更新、删除 |
| `access_key` | 查询参数 `?access_key=...` | 访问设置了访问密码的已发布 Paste |
| `encryption_key` | 查询参数或 `X-Encryption-Key` | 解密内容和文件，或继续写入发布后的 server 模式 Paste |

---

## 写入内容

### `POST /api/pastes/{paste_id}/content`

写入或更新 Paste 文本内容。

**认证：** 需要 `X-Paste-Admin-Key`

**请求头：**

```http
X-Paste-Admin-Key: your_admin_key
Content-Type: application/json
```

发布后的 `server` 模式 Paste 继续写入时，还需要：

```http
X-Encryption-Key: your_encryption_key
```

**请求体：**

| 字段 | 适用模式 | 说明 |
|------|----------|------|
| `content` | `server` | 明文内容 |
| `encrypted_content` | `client` | 客户端加密后的内容 |

---

## 初始化文件上传

### `POST /api/pastes/{paste_id}/files/init`

创建一个分片上传会话。

**认证：** 需要 `X-Paste-Admin-Key`

**请求头：**

```http
X-Paste-Admin-Key: your_admin_key
Content-Type: application/json
```

发布后的 `server` 模式 Paste 继续上传文件时，还需要：

```http
X-Encryption-Key: your_encryption_key
```

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `encryption_mode` | string | 否 | `server` 或 `client`。不传则沿用 Paste 的模式 |
| `file_name` | string | 是 | `server` 模式传明文文件名；`client` 模式传加密后的 Base64 文件名 |
| `mime_type` | string | 否 | MIME 类型，默认 `application/octet-stream` |
| `file_size` | integer | 是 | 原始文件大小，字节 |
| `requested_chunk_size` | integer | 否 | 期望分片大小。服务端可能按配置调整 |

**返回示例：**

```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "chunk_size": 2097152,
  "total_chunks": 3,
  "expires_at": "2026-05-01T12:34:56Z",
  "max_total_upload_size": 1073741824,
  "remaining_upload_size": 1071644672,
  "aad_prefix": "mb:filechunk:v1",
  "aad_required": true,
  "iv_scheme": "prefix8=sha256(upload_id)[:8]; iv=prefix8||chunk_index_u32be"
}
```

后续上传分片时，应使用服务端返回的 `chunk_size`。

---

## 查询上传状态

### `GET /api/pastes/{paste_id}/files/{upload_id}/status`

查询当前上传进度，用于断点续传。

**认证：** 需要 `X-Paste-Admin-Key`

**返回字段：**

| 字段 | 说明 |
|------|------|
| `upload_id` | 上传会话 ID，也是最终 `file_id` |
| `encryption_mode` | `server` 或 `client` |
| `file_size` | 原始文件大小 |
| `chunk_size` | 明文分片大小 |
| `total_chunks` | 总分片数 |
| `uploaded_chunks` | 已上传的分片索引 |
| `uploaded_count` | 已上传分片数量 |
| `next_index` | 建议继续上传的分片索引 |
| `completed` | 分片是否已全部上传 |

---

## 上传分片

### `PUT /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}`

上传单个文件分片。

**认证：** 需要 `X-Paste-Admin-Key`

**请求头：**

```http
X-Paste-Admin-Key: your_admin_key
Content-Type: application/octet-stream
```

请求体必须是原始二进制数据，不是 JSON，也不是 Base64 字符串。

| 模式 | 上传内容 |
|------|----------|
| `server` | 文件切片后的原始字节 |
| `client` | 客户端加密后的分片字节，格式为 `IV(12 bytes) + ciphertext + tag(16 bytes)` |

`client` 模式下，IV 需要使用以下规则：

```text
iv = sha256(upload_id)[:8] + chunk_index_u32be
```

---

## 完成上传

### `POST /api/pastes/{paste_id}/files/{upload_id}/complete`

通知服务端所有分片已上传完毕。服务端会校验分片、合并文件并生成 manifest。

**认证：** 需要 `X-Paste-Admin-Key`

**请求头：**

```http
X-Paste-Admin-Key: your_admin_key
Content-Type: application/json
```

发布后的 `server` 模式 Paste 继续上传文件时，还需要：

```http
X-Encryption-Key: your_encryption_key
```

**请求体：**

可以传空对象：

```json
{}
```

也可以附带校验信息：

```json
{
  "checksum_sha256": "64_hex_characters",
  "chunk_hashes_sha256": [
    "64_hex_characters_for_chunk_0",
    "64_hex_characters_for_chunk_1"
  ]
}
```

| 字段 | 说明 |
|------|------|
| `checksum_sha256` | 整个原始文件的 SHA256。仅 `server` 模式可由服务端验证 |
| `chunk_hashes_sha256` | 每个分片的 SHA256。`server` 模式为明文分片哈希，`client` 模式为加密分片哈希 |

**返回示例：**

```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "max_total_upload_size": 1073741824,
  "remaining_upload_size": 1071644672
}
```

---

## 取消上传

### `POST /api/pastes/{paste_id}/files/{upload_id}/abort`

取消上传会话并清理临时分片。

**认证：** 需要 `X-Paste-Admin-Key`

---

## 删除文件

### `DELETE /api/pastes/{paste_id}/files/{file_id}`

删除已上传完成的文件及其 manifest。

**认证：** 需要 `X-Paste-Admin-Key`

删除后，如果 Paste 内容仍引用该文件链接，需要同步更新内容。

---

## 更新 Paste 设置

### `PUT /api/pastes/{paste_id}`

更新已发布 Paste 的设置。

**认证：** 需要 `X-Paste-Admin-Key`

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 否 | 新标题 |
| `type` | string | 否 | `txt` 或 `md` |
| `expire_time` | string | 否 | `7d`、`30d`、`1y` 或 `never` |
| `max_views` | integer | 否 | `-1` 表示不限制，其余必须大于 0 |
| `access_key` | string | 否 | 新访问密码。空字符串表示关闭访问密码 |

---

## 删除 Paste

### `DELETE /api/pastes/{paste_id}`

删除 Paste 及其文件。

**认证：** 需要 `X-Paste-Admin-Key`

---

## 在 Markdown 中引用文件

上传完成后，可以在 Markdown 内容中引用文件：

```markdown
![截图](/api/pastes/Ab3kL9xQ/files/550e8400-e29b-41d4-a716-446655440000)
```

普通文件可以使用链接：

```markdown
[设计稿.zip](/api/pastes/Ab3kL9xQ/files/550e8400-e29b-41d4-a716-446655440000)
```

---

## 读取 Paste 信息

### `GET /api/pastes/{paste_id}`

获取 Paste 元信息。

**认证：**

- 已发布且未设置访问密码：不需要
- 已发布且设置访问密码：需要 `?access_key=...`
- 草稿：需要 `X-Paste-Admin-Key`

**返回字段：**

| 字段 | 说明 |
|------|------|
| `title` | 标题 |
| `type` | `txt` 或 `md` |
| `status` | `published` 或 `edited` |
| `published_at` | 发布时间 |
| `updated_at` | 更新时间 |
| `expire_at` | 过期时间 |
| `view_count` | 查看次数 |
| `max_views` | 最大查看次数 |

---

## 读取内容

### `GET /api/pastes/{paste_id}/content`

获取 Paste 内容和文件列表。

**认证：**

- 已发布且未设置访问密码：不需要
- 已发布且设置访问密码：需要 `?access_key=...`
- 草稿：需要 `X-Paste-Admin-Key`

**查询参数：**

| 参数 | 说明 |
|------|------|
| `access_key` | 访问设置了密码的 Paste |
| `encryption_key` | 提供后返回解密后的 `content` 和文件名 |

未提供 `encryption_key` 时，返回 `encrypted_content`。

普通访客读取内容会计入查看次数。管理员使用 `X-Paste-Admin-Key` 读取草稿或内容时不计入普通访客查看次数。

---

## 文件元信息

### `GET /api/pastes/{paste_id}/files/{file_id}/meta`

获取文件元信息，包括加密文件名、MIME 类型、文件大小、下载地址和 manifest 地址。

**认证：**

- 已发布且未设置访问密码：不需要
- 已发布且设置访问密码：需要 `?access_key=...`
- 草稿：需要 `X-Paste-Admin-Key`

---

## 文件 Manifest

### `GET /api/pastes/{paste_id}/files/{file_id}/manifest`

获取分片文件的解密描述信息。

**认证：**

- 已发布且未设置访问密码：不需要
- 已发布且设置访问密码：需要 `?access_key=...`
- 草稿：需要 `X-Paste-Admin-Key`

返回内容通常包含：

- `plain_size`
- `chunk_size`
- `total_chunks`
- `chunk_overhead_bytes`
- `aad_format`
- `iv_scheme`
- `iv_prefix`

---

## 下载文件

### `GET /api/pastes/{paste_id}/files/{file_id}`

下载文件。

**认证：**

- 已发布且未设置访问密码：不需要
- 已发布且设置访问密码：需要 `?access_key=...`
- 草稿：需要 `X-Paste-Admin-Key`

**查询参数：**

| 参数 | 说明 |
|------|------|
| `access_key` | 访问设置了密码的 Paste |
| `encryption_key` | 提供后，服务端尽量返回解密后的文件数据和原始文件名 |

该接口支持 HTTP Range：

```http
Range: bytes=start-end
```

未提供或提供错误的 `encryption_key` 时，服务端返回原始加密文件数据。

---

## 常见问题

### `file_name` 可以写成 `filename` 吗？

不可以。初始化上传接口字段名是 `file_name`。

### 分片上传可以发送 JSON 吗？

不可以。`PUT /chunk/{index}` 必须发送二进制数据。

### upload_id 和 file_id 是什么关系？

初始化上传返回的 `upload_id` 会作为最终 `file_id` 使用。

### 文件链接无法访问怎么办？

请确认文件已完成上传，即已经调用 `POST /api/pastes/{paste_id}/files/{upload_id}/complete`。
