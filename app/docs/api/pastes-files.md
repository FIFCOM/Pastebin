# Paste 文件上传

本文介绍 Paste 创建后的进阶操作，包括内容更新、图片与文件上传、大文件分片传输、断点续传，以及文件的读取和下载。

如果你还没有完成基本的 Paste 创建流程，请先阅读 [创建 Paste](/docs/paste-creation)。

> 认证相关内容请参阅 [认证说明](/docs/authentication)。

---

## 概述

文件上传是独立于 Paste 创建的操作，需要在 Paste 创建完成后单独进行。所有上传相关的接口都需要通过请求头传递管理凭据：

```http
X-Paste-Admin-Key: {admin_key}
```

文件上传的完整流程如下：

```text
POST /api/pastes/{paste_id}/files/init                          ← 初始化上传
GET  /api/pastes/{paste_id}/files/{upload_id}/status            ← 查询进度（可选）
PUT  /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}     ← 上传分片
POST /api/pastes/{paste_id}/files/{upload_id}/complete          ← 完成上传
```

几个要点：

- 初始化时返回的 `upload_id` 就是最终的 `file_id`
- 文件上传完成后，可通过以下地址引用该文件：

  ```text
  /api/pastes/{paste_id}/files/{file_id}
  ```

---

## 典型使用流程

创建一个包含图片的 Markdown Paste，通常按以下顺序操作：

```text
1. POST /api/pastes                           创建草稿
2. POST /api/pastes/{id}/files/init           初始化文件上传
3. PUT  /api/pastes/{id}/files/{uid}/chunk/0  上传文件分片
4. POST /api/pastes/{id}/files/{uid}/complete  完成上传
5. POST /api/pastes/{id}/content              写入内容，引用文件地址
6. POST /api/pastes/{id}/publish              发布
```

建议**先上传文件，再将文件地址写入内容**，最后发布。

---

## 认证与权限

### 写入类接口

以下接口均需要 `admin_key`：

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

### 读取类接口

读取类接口的认证方式取决于 Paste 的访问设置：

| 方式 | 适用场景 |
|------|----------|
| 无需凭据 | 已发布且未设置访问密码的 Paste |
| `?access_key=...` | 已发布且设置了访问密码的 Paste |
| `?encryption_key=...` | 需要获取解密后的内容或文件 |
| `X-Paste-Admin-Key: {admin_key}` | 管理员身份访问，可读取草稿 |

> **注意区分三种凭据：**
> - `access_key`：访问密码，控制是否能查看 Paste
> - `encryption_key`：加密密钥，控制是否能解密内容
> - `admin_key`：管理密钥，控制是否能修改 Paste
>
> 这三者应当作为敏感信息保管，避免出现在公开链接、日志或第三方页面中。

---

## 接口详细说明

### POST /api/pastes/{paste_id}/content

写入或更新 Paste 的文本内容。

**请求头：**

```http
X-Paste-Admin-Key: {admin_key}
Content-Type: application/json
```

如果 Paste 已发布且使用 `server` 模式，还需要传递加密密钥：

```http
X-Encryption-Key: {encryption_key}
```

**请求参数（二选一）：**

| 字段 | 适用模式 | 说明 |
|------|----------|------|
| `content` | `server` | 明文内容 |
| `encrypted_content` | `client` | 加密后的 Base64 字符串 |

请确保字段与加密模式匹配，否则会返回错误。

---

### POST /api/pastes/{paste_id}/files/init

初始化一个文件上传会话。

**请求头：**

```http
X-Paste-Admin-Key: {admin_key}
Content-Type: application/json
```

如果 Paste 已发布且使用 `server` 模式，还需要：

```http
X-Encryption-Key: {encryption_key}
```

**请求参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `encryption_mode` | string | 否 | 不传则沿用 Paste 的加密模式 |
| `file_name` | string | 是 | 文件名。`server` 模式传明文；`client` 模式需传加密后的 Base64 字符串 |
| `mime_type` | string | 否 | MIME 类型，默认为 `application/octet-stream` |
| `file_size` | integer | 是 | 文件大小（字节） |
| `requested_chunk_size` | integer | 否 | 期望的分片大小，服务端可能会调整 |

**返回示例：**

```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "chunk_size": 2097152,
  "total_chunks": 3,
  "expires_at": "2026-04-18T12:34:56Z",
  "max_total_upload_size": 104857600,
  "remaining_upload_size": 103809024,
  "aad_prefix": "mb:filechunk:v1",
  "aad_required": true,
  "iv_scheme": "prefix8=sha256(upload_id)[:8]; iv=prefix8||chunk_index_u32be"
}
```

**注意事项：**

1. 返回的 `upload_id` 就是最终的 `file_id`，无需额外映射
2. 后续上传分片时，应使用服务端返回的 `chunk_size`，而非本地指定的值
3. 初始化操作会占用 Paste 的上传配额，返回值中可查看剩余容量

---

### GET /api/pastes/{paste_id}/files/{upload_id}/status

查询当前上传进度，主要用于断点续传场景。

**请求头：**

```http
X-Paste-Admin-Key: {admin_key}
```

**返回字段：**

| 字段 | 说明 |
|------|------|
| `uploaded_chunks` | 已上传的分片索引列表 |
| `uploaded_count` | 已上传的分片数量 |
| `next_index` | 建议从该索引继续上传 |
| `completed` | 是否所有分片均已上传完成 |

**请求示例：**

```bash
curl http://localhost:8000/api/pastes/Ab3kL9xQ/files/550e8400-e29b-41d4-a716-446655440000/status \
  -H 'X-Paste-Admin-Key: your_admin_key'
```

---

### PUT /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}

上传单个文件分片。

**请求头：**

```http
X-Paste-Admin-Key: {admin_key}
Content-Type: application/octet-stream
```

**请求体必须是原始二进制数据**，不是 JSON，也不是 Base64 字符串。具体来说：

- `server` 模式：发送文件切片后的原始字节
- `client` 模式：发送客户端加密后的分片字节

**请求示例：**

```bash
curl -X PUT \
  'http://localhost:8000/api/pastes/Ab3kL9xQ/files/550e8400-e29b-41d4-a716-446655440000/chunk/0' \
  -H 'X-Paste-Admin-Key: your_admin_key' \
  -H 'Content-Type: application/octet-stream' \
  --data-binary @chunk-0.bin
```

**返回示例：**

```json
{
  "message": "分片上传成功",
  "timestamp": 1776501234
}
```

**分片大小要求：**

服务端会严格校验每个分片的大小：

- `server` 模式：分片长度必须等于明文数据的大小
- `client` 模式：分片长度必须等于明文大小 + 12 字节（IV）+ 16 字节（Tag）

**client 模式的加密要求：**

如果你在实现兼容 Web 编辑器的客户端，每个分片需要先在客户端加密后再上传。上传的字节格式为：

```text
IV (12 字节) + 密文 + Tag (16 字节)
```

IV 的生成规则：

```text
iv = sha256(upload_id)[:8] + chunk_index_u32be
```

AAD 需要匹配服务端返回的 `aad_prefix` 格式。

如果不想处理这套加密逻辑，建议将 Paste 改为 `server` 模式。

---

### POST /api/pastes/{paste_id}/files/{upload_id}/complete

通知服务端所有分片已上传完毕。服务端将校验分片完整性、合并文件并生成 `manifest`。

**请求头：**

```http
X-Paste-Admin-Key: {admin_key}
Content-Type: application/json
```

如果 Paste 已发布且使用 `server` 模式，还需要：

```http
X-Encryption-Key: {encryption_key}
```

**请求体：**

可以传空对象，也可以附带校验信息：

```json
{
  "checksum_sha256": "整个文件的 SHA256（可选）",
  "chunk_hashes_sha256": [
    "第 0 片的 SHA256",
    "第 1 片的 SHA256"
  ]
}
```

| 字段 | 说明 |
|------|------|
| `checksum_sha256` | 整个文件的 SHA256 校验值。仅 `server` 模式下服务端可重新计算并验证 |
| `chunk_hashes_sha256` | 每个分片的 SHA256。`server` 模式为明文分片的哈希，`client` 模式为加密分片的哈希 |

**返回示例：**

```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "max_total_upload_size": 104857600,
  "remaining_upload_size": 103809024
}
```

返回的 `file_id` 即为后续引用该文件时使用的标识。

---

### POST /api/pastes/{paste_id}/files/{upload_id}/abort

取消当前上传会话并清理已上传的临时分片。

**请求头：**

```http
X-Paste-Admin-Key: {admin_key}
```

**适用场景：**

- 用户主动取消上传
- 本地分片数据损坏，不再复用当前会话
- 上传中断后决定重新初始化

---

### DELETE /api/pastes/{paste_id}/files/{file_id}

删除已上传完成的文件及其 `manifest`。

**请求头：**

```http
X-Paste-Admin-Key: {admin_key}
```

删除后，如果内容中仍然引用了该文件的链接，请记得同步更新。

---

## 在 Markdown 中引用文件

文件上传完成后，可以通过以下地址在 Paste 内容中引用：

```text
/api/pastes/{paste_id}/files/{file_id}
```

**插入图片：**

```markdown
![截图](/api/pastes/Ab3kL9xQ/files/550e8400-e29b-41d4-a716-446655440000)
```

**插入文件下载链接：**

```markdown
[设计稿.zip](/api/pastes/Ab3kL9xQ/files/550e8400-e29b-41d4-a716-446655440000)
```

Web 端对这类内部链接有特殊处理：图片会尝试解密并预览，普通文件会跳转到下载页面。如果你需要生成与 Web 编辑器兼容的 Markdown，请使用上述格式。

---

## 读取内容与文件

### GET /api/pastes/{paste_id}/content

获取 Paste 的文本内容和文件列表。

**查询参数：**

| 参数 | 说明 |
|------|------|
| `access_key` | 设置了访问密码的 Paste 需要提供 |
| `encryption_key` | 提供后可获取解密后的明文内容 |

**返回说明：**

- 未提供 `encryption_key` 时，返回 `encrypted_content`（加密内容）
- 提供正确的 `encryption_key` 后，返回解密后的 `content`
- 同时返回 `files` 数组，包含该 Paste 下的所有文件

> 对普通访客而言，此接口会计入 Paste 的查看次数。如果设置了 `max_views` 限制，也会在此处生效。

---

### GET /api/pastes/{paste_id}/files/{file_id}/meta

获取文件的元信息，包括：

- 文件名（加密模式下为加密后的文件名）
- MIME 类型
- 文件大小（加密后 / 原始大小）
- 下载地址和 manifest 地址

适用于自行实现下载器或前端预览功能的场景。

---

### GET /api/pastes/{paste_id}/files/{file_id}/manifest

获取分片文件的解密描述信息，通常包含：

- `plain_size`（原始大小）
- `chunk_size`（分片大小）
- `total_chunks`（总分片数）
- `chunk_overhead_bytes`（加密开销）
- `aad_format`、`iv_scheme`、`iv_prefix`（加密参数）

如果你需要在客户端实现分片解密、流式下载或图片预览，需要先获取 `manifest`。

---

### GET /api/pastes/{paste_id}/files/{file_id}

下载文件。

**查询参数：**

| 参数 | 说明 |
|------|------|
| `access_key` | 设置了访问密码的 Paste 需要提供 |
| `encryption_key` | 提供后，服务端会返回解密后的文件数据 |

**Range 请求支持：**

该接口支持 HTTP Range 请求头，可用于断点续传、大文件分段读取和媒体文件流式播放：

```http
Range: bytes=start-end
```

**关于 encryption_key：**

- 提供正确的 `encryption_key` 时，服务端返回解密后的文件数据和原始文件名
- 未提供时，返回加密后的原始数据，文件名为占位名称

如果你希望完全自行控制解密过程，建议按以下顺序调用：

1. `GET .../files/{file_id}/meta` — 获取元信息
2. `GET .../files/{file_id}/manifest` — 获取解密参数
3. `GET .../files/{file_id}` — 下载文件数据

---

## 两种接入方式对比

### 方式 A：简化接入（推荐新手使用）

适用于脚本、后端服务和自动化任务。

- 创建 Paste 时选择 `server` 模式
- 内容直接发送明文
- 文件直接上传原始分片
- 发布后保存好 `encryption_key`

优点：接入简单，无需实现加密逻辑。

### 方式 B：完全兼容 Web 编辑器

适用于需要与 Web 端保持一致体验的客户端。

- 创建 Paste 时选择 `client` 模式
- 文本内容在客户端加密后上传 `encrypted_content`
- 文件名加密为 Base64 后传入 `file_name`
- 每个分片在客户端加密后再上传
- Markdown 中使用内部文件地址

优点：与 Web 编辑器行为完全一致，适合浏览器端的端到端加密场景。

---

## 常见问题

### file_name 字段名写错

初始化上传接口要求的字段名是 `file_name`（带下划线），不是 `filename`。

### 分片上传时发送了 JSON 格式

`PUT /chunk/{index}` 必须发送原始二进制数据，不能是 JSON 或 Base64 字符串。

### upload_id 和 file_id 的关系

在当前实现中，`upload_id` 和 `file_id` 是同一个值，无需额外做映射。

### 文件链接无法访问

如果 Markdown 中引用了文件地址，但文件尚未完成上传（未调用 `complete`），该链接将无法访问。请确保先完成文件上传，再将地址写入内容。

### 混淆 access_key 和 encryption_key

两者用途不同：

- `access_key`：控制能否访问 Paste
- `encryption_key`：控制能否解密内容

### 文件重复上传

Web 端会在前端做同会话内的重复文件过滤，但 API 本身不提供自动去重。直接调用 API 时，重复上传同一文件是允许的。

---

## 完整示例：创建带图片的 Markdown Paste

```text
1. POST /api/pastes                                    创建草稿
2. POST /api/pastes/{id}/files/init                    初始化图片上传
3. PUT  /api/pastes/{id}/files/{upload_id}/chunk/0     上传图片分片
4. POST /api/pastes/{id}/files/{upload_id}/complete     完成上传
5. POST /api/pastes/{id}/content                        写入 Markdown，引用图片地址
   内容示例：![demo](/api/pastes/{id}/files/{file_id})
6. POST /api/pastes/{id}/publish                        发布
```

---

## 接口速查表

| 接口 | 说明 |
|------|------|
| `POST /api/pastes/{paste_id}/content` | 写入或更新文本内容 |
| `POST /api/pastes/{paste_id}/files/init` | 初始化文件上传 |
| `GET /api/pastes/{paste_id}/files/{upload_id}/status` | 查询上传进度 |
| `PUT /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}` | 上传文件分片 |
| `POST /api/pastes/{paste_id}/files/{upload_id}/complete` | 完成文件上传 |
| `POST /api/pastes/{paste_id}/files/{upload_id}/abort` | 取消上传 |
| `DELETE /api/pastes/{paste_id}/files/{file_id}` | 删除已上传的文件 |
| `GET /api/pastes/{paste_id}/content` | 获取内容和文件列表 |
| `GET /api/pastes/{paste_id}/files/{file_id}/meta` | 获取文件元信息 |
| `GET /api/pastes/{paste_id}/files/{file_id}/manifest` | 获取分片解密描述 |
| `GET /api/pastes/{paste_id}/files/{file_id}` | 下载文件 |
