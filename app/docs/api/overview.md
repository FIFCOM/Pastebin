# API 文档

欢迎使用 Material Bin API 文档。本文档面向需要通过程序调用 Material Bin 接口的开发者。

---

## 文档结构

| 模块 | 内容 |
|------|------|
| [认证](/docs/authentication) | API Key 的获取、传递方式与适用范围 |
| [创建 Paste](/docs/paste-creation) | 从创建草稿到发布的完整流程 |
| [Paste 文件上传](/docs/pastes-files) | 图片与文件的上传、分片传输、断点续传、下载与解密 |

---

## 涵盖的接口

本文档覆盖以下两类接口：

- **用户接口**：账户管理、密钥管理、会话管理、两步验证等接口，统一使用 `access_token`
- **Paste 接口**：包括公开的创建接口，以及基于 `X-Paste-Admin-Key` 的内容写入、文件上传、发布等接口

---

## 快速开始

`Authorization` 仅用于用户身份凭据。当前若接口会读取 API Key，仍通过 `Authorization` 请求头传递：

```http
Authorization: Bearer pk_你的API密钥
```

API Key 以 `pk_` 开头，创建时返回完整密钥。密钥明文只显示一次，请妥善保存。

需要区分 API Key 与 `access_token` 的适用范围时，请参阅 [认证](/docs/authentication)。

---

## 参考资料

以下为自动生成的接口文档，可作为辅助参考：

- [Swagger UI](/api/openapi/docs)
- [ReDoc](/api/openapi/redoc)
- [OpenAPI JSON](/api/openapi.json)
