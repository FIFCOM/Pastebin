# API 文档侧边栏入口落地与手写文档页

## TL;DR
> **Summary**: 将首页侧边栏里的 `API文档` 占位入口实现为站内多页面 API 文档区，文档内容采用手写 Markdown，复用现有 `markdown-it` 渲染链路，并聚焦两类内容：可使用 API Key 的接口与 Paste 相关接口。
> **Deliverables**:
> - 站内 API 文档路由与页面壳层
> - 侧边栏真实入口与文档模块导航
> - 聚焦 API Key 与 Paste 的手写 Markdown API 文档
> - 与当前后端接口一致的鉴权/错误/流程说明
> **Effort**: Medium
> **Parallel**: NO
> **Critical Path**: 1 → 2 → 3 → 4 → 5 → 6

## Context
### Original Request
- 首页侧边栏已有一个 API 文档占位入口。
- 目标是把它实现成给用户查看的完善 API 文档。
- 文档应为手写 Markdown，并使用现有 `markdown-it` 渲染。
- 可以参考 Swagger / ReDoc，但内容必须重写且更清晰。
- 只做阅读型文档，不提供 Try it out。

### Interview Summary
- 文档范围调整为：**只实现两类内容：可使用 API Key 的接口 + Paste 相关接口**。
- 排除范围：`/api/internal/*`、`/api/install/*`、在线调试、测试基建扩展。
- 推荐 IA：**多篇 Markdown 文档**，而不是单页长文档。
- 文档应为站内页面，不直接把 Swagger/ReDoc 当最终体验，但可作为辅助参考链接保留。
- 非 API Key、非 Paste 的接口不进入正文主模块。

### Metis Review (gaps addressed)
- 已冻结范围：只做“API Key + Pastes 文档、现有 renderer、路由/侧边栏整合”。
- 已显式排除 Swagger/Redoc 嵌入、Try-it-out、自动生成文档、搜索、SDK 代码片段、`/api/internal/*`、`/api/install/*`。
- 已确定文档需覆盖多种鉴权模型的清晰说明，并采用中心化导航配置，避免侧边栏死链和内容漂移。
- 默认采用**真实多路由文档区**而不是单页 query-tab，以支持直达、刷新、深链接和模块化维护。

## Work Objectives
### Core Objective
- 交付一个对终端用户友好的、站内可访问的 API 文档区：从首页侧边栏进入，支持按模块浏览，以手写 Markdown 清晰解释 **可使用 API Key 的接口** 与 **Paste 相关接口** 的使用方式和认证边界。

### Deliverables
- `web/src/views/ApiDocsView.vue` 文档阅读页。
- `web/src/content/api-docs/` 下的 Markdown 文档集合与内容清单。
- `web/src/components/docs/` 下的文档导航/配置源（如导航常量、section manifest）。
- `web/src/router/index.ts` 中的 `/api-docs` 路由集合。
- `web/src/components/AppSidebar.vue` 中的真实 API 文档入口和文档态侧边栏导航。
- `web/src/App.vue` 中的文档路由侧边栏显示规则。

### Included Endpoint Families (authoritative)
> **最终锁定范围**：正文只实现“支持用 `Bearer pk_...` API Key 访问”的接口，以及全部 Paste 相关接口。
> 除下列接口外，其余接口均不进入首版正文。

- `overview`
  - 不承载独立接口；只说明范围、阅读方式、模块划分、原始参考链接。

- `authentication`
  - 只说明 API Key 的格式、Header 传递方式、以及如何先登录后创建第一个 API Key。

- `paste-creation`
  - `POST /api/pastes`
  - 必须明确标注：这是公开接口，**不消费 API Key，也不要求认证**。
  - 必须解释它返回 `admin_key`，后续 paste 内容写入/发布/文件上传依赖 `admin_key` 而不是用户 API Key。

- `pastes-files`
  - `POST /api/pastes/{paste_id}/content`
  - `POST /api/pastes/{paste_id}/files/init`
  - `GET /api/pastes/{paste_id}/files/{upload_id}/status`
  - `PUT /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}`
  - `POST /api/pastes/{paste_id}/files/{upload_id}/complete`
  - `POST /api/pastes/{paste_id}/files/{upload_id}/abort`
  - `DELETE /api/pastes/{paste_id}/files/{file_id}`
  - `POST /api/pastes/{paste_id}/publish`
  - `GET /api/pastes/{paste_id}`
  - `GET /api/pastes/{paste_id}/content`
  - `GET /api/pastes/{paste_id}/files/{file_id}/manifest`
  - `GET /api/pastes/{paste_id}/files/{file_id}/meta`
  - `GET /api/pastes/{paste_id}/files/{file_id}`
  - `PUT /api/pastes/{paste_id}`
  - `DELETE /api/pastes/{paste_id}`
  - 必须区分公开访问、`access_key`、`encryption_key`、`admin_key` 四种访问条件。

- `account-security`
  - `POST /api/users/logout-all`
  - `GET /api/users/me`
  - `GET /api/users/{user_id}`
  - `PUT /api/users/{user_id}`
  - `DELETE /api/users/{user_id}`
  - `DELETE /api/users/sessions/{session_id}`
  - `GET /api/users/me/totp`
  - `POST /api/users/me/totp`
  - `POST /api/users/me/totp/verify`
  - `DELETE /api/users/me/totp`

- `api-keys`
  - `GET /api/user/apikeys`
  - `POST /api/user/apikeys`
  - `DELETE /api/user/apikeys/{key_id}`
  - `POST /api/user/apikeys/cleanup-expired`

- `collaboration`
  - `POST /api/rooms/member-token`
  - `POST /api/rooms/member-token/refresh`

### Final Locked API Key Endpoint List
- 普通/自有账户能力
  - `POST /api/users/logout-all`
  - `GET /api/users/me`
  - `GET /api/users/{user_id}`
  - `PUT /api/users/{user_id}`
  - `DELETE /api/users/{user_id}`
  - `DELETE /api/users/sessions/{session_id}`
  - `GET /api/users/me/totp`
  - `POST /api/users/me/totp`
  - `POST /api/users/me/totp/verify`
  - `DELETE /api/users/me/totp`

- API Key 自管理
  - `GET /api/user/apikeys`
  - `POST /api/user/apikeys`
  - `DELETE /api/user/apikeys/{key_id}`
  - `POST /api/user/apikeys/cleanup-expired`

- 管理员专属（仅当 API Key 属于管理员用户时）
  - `GET /api/users`
  - `POST /api/users`
  - `POST /api/users/cleanup-sessions`

### Final Locked Paste Endpoint List
- `POST /api/pastes`
- `POST /api/pastes/{paste_id}/content`
- `POST /api/pastes/{paste_id}/files/init`
- `GET /api/pastes/{paste_id}/files/{upload_id}/status`
- `PUT /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}`
- `POST /api/pastes/{paste_id}/files/{upload_id}/complete`
- `POST /api/pastes/{paste_id}/files/{upload_id}/abort`
- `DELETE /api/pastes/{paste_id}/files/{file_id}`
- `POST /api/pastes/{paste_id}/publish`
- `GET /api/pastes/{paste_id}`
- `GET /api/pastes/{paste_id}/content`
- `GET /api/pastes/{paste_id}/files/{file_id}/manifest`
- `GET /api/pastes/{paste_id}/files/{file_id}/meta`
- `GET /api/pastes/{paste_id}/files/{file_id}`
- `PUT /api/pastes/{paste_id}`
- `DELETE /api/pastes/{paste_id}`

### Explicit Exclusions (authoritative)
- `/api/internal/*`
- `/api/install/*`
- `GET /api/health`
- `GET /api/config`
- 所有 `/api/user/history/*`
- `POST /api/users/refresh`
- `POST /api/users/logout`
- `GET /api/users/{user_id}/sessions`
- `DELETE /api/users/{user_id}/sessions/others`

### API Key Access Matrix (authoritative)
> 判定规则必须以依赖注入为准，而不是按模块名猜测。
> 这份矩阵描述“真实能力边界”；其中部分接口虽然技术上支持 API Key，但若被列入 `Explicit Exclusions`，正文仍只做简短说明或不展开。
>
> - `Depends(get_current_user)` → **支持** `Bearer pk_...` API Key
> - `Depends(get_optional_user)` → **可选支持** `Bearer pk_...` API Key
> - `Depends(get_current_user_and_session)` → **不支持** API Key
> - `Depends(get_current_user_with_key)` → **不支持** API Key
> - 使用 `admin_key` / `member_token` / `refresh cookie` / `access_key` / `encryption_key` 的接口，不等同于支持用户 API Key

#### Confirmed API Key-capable endpoints
- 账户与用户接口（依赖 `get_current_user`）
  - `POST /api/users/logout-all`
  - `GET /api/users/me`
  - `GET /api/users/{user_id}`
  - `PUT /api/users/{user_id}`
  - `DELETE /api/users/{user_id}`
  - `GET /api/users`
  - `POST /api/users`
  - `DELETE /api/users/sessions/{session_id}`
  - `POST /api/users/cleanup-sessions`
  - `GET /api/users/me/totp`
  - `POST /api/users/me/totp`
  - `POST /api/users/me/totp/verify`
  - `DELETE /api/users/me/totp`

- API Key 自管理接口（依赖 `get_current_user`）
  - `GET /api/user/apikeys`
  - `POST /api/user/apikeys`
  - `DELETE /api/user/apikeys/{key_id}`
  - `POST /api/user/apikeys/cleanup-expired`

- 协作中的“可选用户识别”接口（依赖 `get_optional_user`，允许 API Key 但不是必需）
  - `POST /api/rooms/member-token`
  - `POST /api/rooms/member-token/refresh`

#### Confirmed non-API-Key endpoints
- 仅支持 access session，不支持 API Key（依赖 `get_current_user_and_session`）
  - `GET /api/users/{user_id}/sessions`
  - `DELETE /api/users/{user_id}/sessions/others`

- 需要恢复用户密钥，不支持 API Key（依赖 `get_current_user_with_key`）
  - `GET /api/user/history`
  - `POST /api/user/history/import_guest`
  - `POST /api/user/history/{paste_id}`
  - `GET /api/user/history/{paste_id}`
  - `PUT /api/user/history/{paste_id}/star`
  - `DELETE /api/user/history/{paste_id}`

- 使用其他认证模型，不支持用户 API Key
  - `POST /api/users/register`
  - `POST /api/users/login`
  - `POST /api/users/login-totp`
  - `POST /api/users/refresh`
  - `POST /api/users/logout`
  - 所有 `/api/pastes/*` 写接口（依赖 `admin_key`）
  - 所有 `/api/pastes/*` 读接口（依赖公开访问、`access_key`、`encryption_key` 或 `admin_key`）
  - `POST /api/rooms`
  - `GET /api/join/{pin_code}`
  - `POST /api/rooms/{room_id}/join`
  - `GET /api/rooms/{room_id}/members`
  - `POST /api/rooms/{room_id}/pastes`
  - `GET /api/rooms/{room_id}/pastes`
  - `DELETE /api/rooms/{room_id}/leave`
  - `WS /api/rooms/{room_id}/ws`

### Research Note: Likely API Key Compatibility Gaps
> 这是基于当前代码语义给出的“明显应考虑兼容 API Key，但尚未实现”的候选，不代表本次首版文档范围自动扩张。

#### High-confidence candidates
- `POST /api/pastes`
  - 现状：`app/controllers/paste_controller.py:259-273` 完全公开，不消费 `Authorization`，因此 API Key 传入也不会生效。
  - 为什么明显：这是最典型的程序化调用入口；对外提供 API Key 后，自动化创建 paste 是最自然的能力。
  - 当前缺口：`app/models/paste.py:24-76` 没有 `user_id/owner_id`，`app/services/paste_service.py:744-805` 也不会把 paste 归属到用户，因此“兼容 API Key”若只是允许带上 `pk_` 而不做任何归属处理，价值有限。

- `GET /api/users/{user_id}/sessions`
  - 现状：控制器依赖 `get_current_user_and_session`，所以 API Key 被硬性拒绝；见 `app/controllers/user_controller.py:360-379` 与 `app/core/dependencies.py:114-131`。
  - 为什么明显：这是自助查看自己会话的只读接口，语义上与 `DELETE /api/users/sessions/{session_id}` 一样属于账户管理；后者已经兼容 API Key。
  - 当前缺口：其实主要是依赖选型问题，而不是业务模型问题；`app/services/user_service.py:505-527` 已接受 `current_session_id: str | None`，因此在 API Key 场景下传 `None` 并把 `is_current` 全部标成 `false` 就能成立。

#### Not obvious / blocked by deeper design
- `DELETE /api/users/{user_id}/sessions/others`
  - 不明显。该接口语义要求“保留当前 session，撤销其他 session”；API Key 场景下没有 current session 概念，直接兼容会改变接口含义。

- 所有 `GET/POST/PUT/DELETE /api/user/history/*`
  - 不明显。它们依赖 `get_current_user_with_key`，而 `app/core/dependencies.py:151-199` 明确需要恢复用户密钥；当前 API Key 认证并不具备这条密钥恢复链路。

- 所有 `/api/pastes/{paste_id}/*` 管理接口与文件上传接口
  - 不明显。它们当前围绕 `admin_key` 设计，而不是用户身份；在 `Paste` 尚无 owner 字段前，无法定义“某个 API Key 是否有权管理某个 paste”。

- 协作房间核心操作（创建房间、加入房间、成员列表、分享 paste、WebSocket）
  - 不明显。它们围绕 `member_token` 协议设计，API Key 更适合作为“换取 member token 的前置身份”，而不是直接替代 member token。

### Definition of Done (verifiable conditions with commands)
- `cd web && npm run build` 成功。
- 启动后端后，`curl -sf http://127.0.0.1:8000/openapi.json > /tmp/material-bin-openapi.json` 成功，用于对照校验接口范围。
- 启动前后端后，Playwright 能稳定访问 `/api-docs/overview` 并完成模块导航、锚点跳转、硬刷新与移动端检查。
- 文档页面不会在运行时依赖 `/docs`、`/redoc`、`/openapi.json` 才能渲染主体内容。
- 渲染后的文档中不出现 `/api/internal/` 与 `/api/install` 的正文内容。

### Must Have
- API 文档对未登录用户可读。
- 文档采用中心化导航源，文件与路由一一对应。
- 默认入口为 `/api-docs` → 重定向到 `/api-docs/overview`。
- 文档覆盖以下模块：Overview、Authentication（API Key 基础与获取说明）、Paste Creation、Pastes & Files、Account & Security、API Keys、Collaboration（仅 member-token 两个入口）。
- 文档正文严格覆盖上方“Included Endpoint Families”中的接口，不允许执行者自行增删范围。
- 文档必须显式标注哪些接口支持 `Bearer pk_...` API Key，哪些明确不支持；判定依据必须来自依赖注入实现。
- 文档明确写出不同接口使用的认证方式与限制。
- 保留 `/docs`、`/redoc`、`/openapi.json` 为“原始参考链接”，但不作为正文主体。

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- 不嵌入 Swagger UI / ReDoc。
- 不做 Try it out。
- 不从 `/openapi.json` 运行时自动生成页面内容。
- 不文档化 `/api/internal/*`、`/api/install/*`、`/api/user/history/*`、`POST /api/users/refresh`、`POST /api/users/logout`、`GET /api/users/{user_id}/sessions`、`DELETE /api/users/{user_id}/sessions/others`。
- 不引入新的 Markdown 渲染器。
- 不新增测试框架、CI、搜索、版本切换、SDK 生成。

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: none + existing manual/agent QA only; build gate is `cd web && npm run build`
- QA policy: Every task includes agent-executed scenarios with stable selectors / explicit URLs / exact commands
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
> 本计划按**单一收敛范围**执行，不分阶段扩张范围。

Single flow: manifest → docs content → page shell → sidebar/routing → polish → verification

### Dependency Matrix (full, all tasks)
- 1 blocks 2, 3, 4, 5, 6
- 2 blocks 4, 6
- 3 blocks 4, 6
- 4 blocks 5, 6
- 5 blocks 6
- 6 blocks Final Verification Wave

### Agent Dispatch Summary (wave → task count → categories)
- Content/structure → 3 tasks → writing, unspecified-low, writing
- UI/integration → 3 tasks → visual-engineering, unspecified-low, visual-engineering
- Final Verification Wave → 4 tasks → oracle / unspecified-high / unspecified-high / deep

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. 建立 API 文档单一事实源与模块边界

  **What to do**: 创建一个中心化的 API 文档 manifest（推荐放在 `web/src/content/api-docs/index.ts`），为每个模块定义：`slug`、标题、分组、排序、侧边栏标签、Markdown 原始文件 loader、是否公开、以及“原始参考链接”列表。固定首版包含的模块为：`overview`、`authentication`、`paste-creation`、`pastes-files`、`account-security`、`api-keys`、`collaboration`。其中 `authentication` 必须承载 API Key 获取方式、格式、Header 传递方式、能力矩阵；`paste-creation` 只覆盖公开的 `POST /api/pastes`；`pastes-files` 覆盖其余 paste/file 相关接口；`collaboration` 只覆盖 `member-token` 两个入口。不要把导航元数据分散到多个常量文件。
  **Must NOT do**: 不要使用运行时请求 `/openapi.json` 生成导航；不要把 Swagger/ReDoc 当内容源；不要把 install/internal/history/session-only 端点混入正文范围。

  **Recommended Agent Profile**:
  - Category: `unspecified-low` - Reason: 这是低风险的结构定义任务，重点是清晰建模与避免重复源。
  - Skills: `[]` - 不需要额外技能。
  - Omitted: [`frontend-design`] - 本任务不是视觉设计。

  **Parallelization**: Can Parallel: NO | Stage: foundation | Blocks: 2, 3, 4, 5, 6 | Blocked By: none

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `web/src/components/users/navigation.ts:18-84` - 现有“中心化导航定义 + 分组”的最佳参考模式。
  - Pattern: `web/src/components/AppSidebar.vue:87-100,137-154,188-203` - 当前侧边栏默认 section、动态 section 计算与点击处理方式。
  - API/Type: `web/src/router/index.ts:5-63` - 顶级页面路由的注册风格。
  - API/Type: `README.md:122-256` - 现有 API 概览与公开说明基线。
  - API/Type: `main.py:80-104` - 后端已注册的公开路由与根信息。
  - API/Type: `app/core/middleware/install_gate.py:19-26,38-63` - 明确说明为什么 `/api/install/*` 必须排除。
  - API/Type: `app/core/dependencies.py:83-168` - 文档必须解释的多认证模型来源。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `web/src/content/api-docs/index.ts`（或计划指定的等价单一事实源文件）存在，并且只从这一处导出 section 顺序、slug、标签与 loader。
  - [ ] section 列表精确包含：`overview`, `authentication`, `paste-creation`, `pastes-files`, `account-security`, `api-keys`, `collaboration`。
  - [ ] manifest 或同级权威常量中明确记录 included endpoint families 与 explicit exclusions。
  - [ ] manifest 或同级权威常量中明确记录 API Key access matrix，并区分 API Key-capable / non-API-Key / optional-API-Key 三类。
  - [ ] manifest 明确声明排除 `internal/install/history/session-only/config/health`。

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Manifest includes exact sections
    Tool: Bash
    Steps: 运行一个短脚本读取 manifest 导出值；断言 section slug 顺序与计划完全一致，且每个 section 都有 title、group、loader、sidebarLabel。
    Expected: 断言全部通过；若缺少任一 slug 或字段，脚本非 0 退出。
    Evidence: .sisyphus/evidence/task-1-docs-manifest.txt

  Scenario: Manifest excludes forbidden scope
    Tool: Bash
    Steps: 读取 manifest 与相关常量文件；断言不存在 `internal`, `install`, `history`, `sessions-self`, `health`, `config` 等被排除模块的 slug/标题。
    Expected: 不出现任何被排除的模块；若出现则脚本非 0 退出。
    Evidence: .sisyphus/evidence/task-1-docs-manifest-exclusions.txt
  ```

  **Commit**: NO | Message: `feat(web): define api docs manifest` | Files: `web/src/content/api-docs/index.ts`

- [ ] 2. 编写概览 / 鉴权 / 创建 Paste / 账户安全文档

  **What to do**: 在 `web/src/content/api-docs/` 下编写至少四篇手写 Markdown：`overview.md`、`authentication.md`、`paste-creation.md`、`account-security.md`。`overview.md` 负责说明首版以 API Key 接口为主，外加 `POST /api/pastes` 这一公开例外；`authentication.md` 必须把“如何获取第一个 API Key”“API Key 的 Header 传递方式”“哪些接口支持 / 不支持 API Key”写清楚，并把 session 登录类接口仅作为引导说明；`paste-creation.md` 只覆盖 `POST /api/pastes`，明确说明它是公开接口、返回 `admin_key`、后续 paste 管理依赖 `admin_key` 而不是用户 API Key；`account-security.md` 覆盖 `POST /api/users/logout-all`、`GET /api/users/me`、`GET/PUT/DELETE /api/users/{user_id}`、`DELETE /api/users/sessions/{session_id}` 与 TOTP 四个接口，并明确 `GET /api/users/{user_id}/sessions`、`DELETE /api/users/{user_id}/sessions/others` 不支持 API Key。
  **Must NOT do**: 不要照抄 Swagger 描述；不要把 `POST /api/pastes` 误写成支持 API Key；不要把 session-only 接口写成支持 API Key；不要省略 refresh cookie 与 API Key 的差异；不要出现 `/api/install` 或 `/api/internal` 正文示例。

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: 任务核心是结构化技术写作而非代码复杂度。
  - Skills: `[]` - 无需额外技能；直接按仓库事实写作。
  - Omitted: [`documentation-writer`] - 当前任务更偏实现型文档落地，直接执行即可。

  **Parallelization**: Can Parallel: YES | Stage: content | Blocks: 4, 6 | Blocked By: 1

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `README.md:96-156` - 现有 README 的 API 组织方式，可作为首层目录顺序基线。
  - API/Type: `app/controllers/user_controller.py:86-237` - 注册、登录、TOTP 登录、refresh、logout、logout-all、`/me` 的真实接口定义。
  - API/Type: `app/controllers/user_controller.py:220-349` - `logout-all`、`/me`、`/{user_id}`、管理员用户接口的真实定义。
  - API/Type: `app/controllers/user_controller.py:360-510` - session-only 接口与 TOTP 的真实范围；`cleanup-sessions` 为管理员能力，应排除。
  - API/Type: `app/core/dependencies.py:83-168` - `get_current_user` / `get_current_user_and_session` 的真实鉴权限制。
  - External: `/docs`, `/redoc`, `/openapi.json` - 仅作为作者交叉核对参考，不作为正文主体验证来源。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `overview.md`、`authentication.md`、`paste-creation.md`、`account-security.md` 均存在，并被 manifest 正确引用。
  - [ ] `authentication.md` 明确区分 `Bearer access token`、`pk_` API Key、`mb_refresh_token`、`admin_key`、`member_token` 的用途与是否属于普通用户文档范围。
  - [ ] `paste-creation.md` 明确说明 `POST /api/pastes` 是公开接口、不消费 API Key、返回 `admin_key` 用于后续 paste 管理。
  - [ ] `account-security.md` 覆盖 API Key 可访问的账户接口与 TOTP，不把 `GET /api/users/{user_id}/sessions`、`DELETE /api/users/{user_id}/sessions/others` 误写成支持 API Key。
  - [ ] `overview.md` 明确写出首版 included modules 与 explicit exclusions，且与本计划一致。
  - [ ] `authentication.md` 或 `overview.md` 明确列出“支持 API Key 访问的接口集合”与“明确不支持 API Key 的接口集合”，并与本计划一致。

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Auth docs contain required token taxonomy
    Tool: Bash
    Steps: 检查 `authentication.md`，确认存在 “Access Token”、“API Key”、“Refresh Token Cookie”、“Paste admin_key”、“Member Token” 五个明确小节或等价标题。
    Expected: 五类鉴权均被准确说明；缺任一项则失败。
    Evidence: .sisyphus/evidence/task-2-auth-docs.txt

  Scenario: Account docs exclude admin-only endpoints
    Tool: Bash
    Steps: 搜索 `account-security.md`，断言不包含 `GET /api/users`、`POST /api/users`、`cleanup-sessions` 等管理员接口正文。
    Expected: forbidden endpoint family 不出现；若出现则失败。
    Evidence: .sisyphus/evidence/task-2-account-docs-exclusions.txt

  Scenario: API Key-capable endpoints are documented accurately
    Tool: Bash
    Steps: 检查 `authentication.md` 与 `account-security.md`；确认文中明确标出 `GET /api/users/me`、`DELETE /api/users/sessions/{session_id}`、TOTP 四个接口、以及 `POST /api/users/logout-all` 支持 API Key；同时确认 `GET /api/users/{user_id}/sessions` 与 `DELETE /api/users/{user_id}/sessions/others` 被标注为不支持 API Key。
    Expected: API Key 支持矩阵与依赖注入实现一致；若任一接口标注错误则失败。
    Evidence: .sisyphus/evidence/task-2-api-key-matrix.txt

  Scenario: Public paste creation exception is documented accurately
    Tool: Bash
    Steps: 检查 `paste-creation.md`；确认存在 `POST /api/pastes`，并明确包含“公开接口”“无需认证”“不消费 API Key”“返回 admin_key”四个要点。
    Expected: 公开例外被准确说明；若被误写成 API Key 接口或遗漏 admin_key 语义则失败。
    Evidence: .sisyphus/evidence/task-2-paste-creation.txt
  ```

  **Commit**: NO | Message: `docs(api): write auth and account guides` | Files: `web/src/content/api-docs/overview.md`, `web/src/content/api-docs/authentication.md`, `web/src/content/api-docs/paste-creation.md`, `web/src/content/api-docs/account-security.md`

- [ ] 3. 编写 API Keys / Pastes / Collaboration / API Key 能力矩阵文档集

  **What to do**: 编写剩余文档：`api-keys.md`、`pastes-files.md`、`collaboration.md`，以及一个专门的 API Key 能力矩阵章节（可放在 `authentication.md` 内，也可拆成 `api-key-capability-matrix.md`）。`api-keys.md` 解释 `GET/POST/DELETE /api/user/apikeys`、`POST /api/users/cleanup-sessions` 以及管理员 API Key 可访问的 `GET/POST /api/users` 的用途、限制和权限边界；`pastes-files.md` 覆盖除 `POST /api/pastes` 外的全部 paste/file 接口，并准确区分公开访问、`access_key`、`encryption_key`、`admin_key`；`collaboration.md` 只解释 `POST /api/rooms/member-token` 与 `POST /api/rooms/member-token/refresh` 这两个允许可选 API Key 识别的接口；能力矩阵章节必须明确列出：支持 API Key、可选支持 API Key、不支持 API Key 三类接口，并说明判定依据来自依赖注入实现。每篇都要给出清晰的请求示例、必需头、成功/失败说明和边界提示。
  **Must NOT do**: 不要遗漏任何 paste/file 接口；不要把房间创建/加入/成员/分享/WebSocket 误写成支持 API Key；不要把 paste/file 接口误写成支持 `pk_` API Key；不要把加密/鉴权前提写得含糊。

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: 大部分工作是基于真实接口重写高可读文档。
  - Skills: `[]` - 无需额外技能。
  - Omitted: [`frontend-design`] - 本任务不涉及页面实现。

  **Parallelization**: Can Parallel: YES | Stage: content | Blocks: 4, 6 | Blocked By: 1

  **References** (executor has NO interview context - be exhaustive):
  - API/Type: `app/controllers/api_key_controller.py:20-86` - API key list/create/delete/cleanup-expired。
  - API/Type: `app/controllers/paste_controller.py:259-1335` - paste 创建、内容写入、发布、文件上传、读取、删除的完整真实定义。
  - API/Type: `app/services/paste_service.py:744-1263` - paste/file 接口背后的真实认证语义，尤其是 `admin_key`、`access_key`、`encryption_key` 的作用边界。
  - API/Type: `app/controllers/collab_room_controller.py:58-104` - member token 与 member token refresh 的真实定义。
  - API/Type: `app/controllers/collab_room_controller.py:107-377` - 其余房间接口与 WebSocket；用于说明为什么这些接口不支持 API Key。
  - API/Type: `app/controllers/user_history_controller.py:30-269` - history 全量依赖 `get_current_user_with_key`，应被矩阵明确标为不支持 API Key。
  - API/Type: `app/controllers/user_controller.py:314-349,419-430` - 管理员 API Key 可访问的用户列表/创建用户/cleanup-sessions。
  - API/Type: `app/core/dependencies.py:83-168` - `get_current_user` / `get_optional_user` / `get_current_user_and_session` / `get_current_user_with_key` 的根本判定依据。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `api-keys.md`、`pastes-files.md`、`collaboration.md` 与 API Key 能力矩阵章节均存在，并被 manifest 或文内导航正确引用。
  - [ ] `api-keys.md` 明确写出四个 `/api/user/apikeys*` 接口均支持 API Key，并额外写明管理员 API Key 可访问的 `GET/POST /api/users` 与 `POST /api/users/cleanup-sessions`。
  - [ ] `pastes-files.md` 完整覆盖 `POST /{paste_id}/content` 到 `DELETE /{paste_id}` 的全部 paste/file 接口，并准确区分 `admin_key` / `access_key` / `encryption_key` / 公开访问。
  - [ ] `collaboration.md` 只覆盖 `member-token` 与 `member-token/refresh`，并明确说明其余协作接口不支持 API Key。
  - [ ] 能力矩阵中对 account/api-keys/collaboration/history/pastes/files 的 API Key 支持结论与本计划一致，无额外 endpoint 漂移。

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: API Keys guide documents self-management endpoints accurately
    Tool: Bash
    Steps: 检查 `api-keys.md`，确认存在 `GET /api/user/apikeys`、`POST /api/user/apikeys`、`DELETE /api/user/apikeys/{key_id}`、`POST /api/user/apikeys/cleanup-expired`，以及管理员专属 `GET /api/users`、`POST /api/users`、`POST /api/users/cleanup-sessions`，并明确标注权限边界。
    Expected: 自管理与管理员 API Key 接口都被准确说明；缺任一项则失败。
    Evidence: .sisyphus/evidence/task-3-api-keys-docs.txt

  Scenario: Paste and file guide covers full lifecycle accurately
    Tool: Bash
    Steps: 检查 `pastes-files.md`，确认存在 `POST /api/pastes/{paste_id}/content`、`POST /api/pastes/{paste_id}/publish`、`GET /api/pastes/{paste_id}`、`GET /api/pastes/{paste_id}/content`、`POST /api/pastes/{paste_id}/files/init`、`GET /api/pastes/{paste_id}/files/{upload_id}/status`、`PUT /api/pastes/{paste_id}/files/{upload_id}/chunk/{index}`、`POST /api/pastes/{paste_id}/files/{upload_id}/complete`、`POST /api/pastes/{paste_id}/files/{upload_id}/abort`、`GET /api/pastes/{paste_id}/files/{file_id}/manifest`、`GET /api/pastes/{paste_id}/files/{file_id}/meta`、`GET /api/pastes/{paste_id}/files/{file_id}`、`DELETE /api/pastes/{paste_id}/files/{file_id}`、`PUT /api/pastes/{paste_id}`、`DELETE /api/pastes/{paste_id}`。
    Expected: paste/file 全链路完整，且没有把它们误标为 API Key 接口；缺任一关键接口则失败。
    Evidence: .sisyphus/evidence/task-3-pastes-files-docs.txt

  Scenario: Collaboration guide limits API Key support correctly
    Tool: Bash
    Steps: 检查 `collaboration.md`，确认正文只覆盖 `POST /api/rooms/member-token` 与 `POST /api/rooms/member-token/refresh` 两个接口；同时断言不把 `POST /api/rooms`、`POST /api/rooms/{room_id}/join`、`GET /api/rooms/{room_id}/members`、`WS /api/rooms/{room_id}/ws` 写成支持 API Key。
    Expected: 可选 API Key 识别范围被准确限制；若误扩范围则失败。
    Evidence: .sisyphus/evidence/task-3-collab-docs.txt

  Scenario: Non-API-Key modules do not falsely claim API Key support
    Tool: Bash
    Steps: 检查 API Key 能力矩阵与相关文档；断言 history 接口被明确标为不支持 API Key，pastes/files 不被误写为支持 `pk_` API Key，collaboration 仅 `member-token` 两个入口允许“可选 API Key 识别”而房间操作接口不被误标。
    Expected: 文档中的 API Key 说明与真实认证模型一致；若出现误标则失败。
    Evidence: .sisyphus/evidence/task-3-non-apikey-matrix.txt
  ```

  **Commit**: NO | Message: `docs(api): write api key and paste guides` | Files: `web/src/content/api-docs/*.md`

- [ ] 4. 实现多页面 Markdown 文档阅读页

  **What to do**: 新建 `web/src/views/ApiDocsView.vue`，基于 route param `section` 从 manifest 加载对应 `?raw` Markdown 内容，并通过现有 `Markdown.vue` 渲染。页面必须包含：文档标题、副标题/简介、模块级本地导航（供移动端和无侧边栏场景使用）、正文容器、加载态、非法 section 的安全回退（统一重定向到 `/api-docs/overview`）。为页面核心节点增加稳定选择器：`data-testid="api-docs-page"`、`api-docs-title`、`api-docs-local-nav`、`api-docs-content`、`api-docs-empty-state`。本地导航必须来自 manifest，而不是手写重复数组。
  **Must NOT do**: 不要新增 markdown renderer；不要通过 HTTP 请求拉取 markdown 文件；不要让非法 `section` 留在空白页面；不要依赖登录态。

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: 这是页面壳层与交互布局任务，既要对接渲染链路，也要保证可用性。
  - Skills: [`frontend-design`] - 需要产出不显得粗糙的阅读页布局。
  - Omitted: [`ui-ux-pro-max`] - 当前页面规模中等，`frontend-design` 足够。

  **Parallelization**: Can Parallel: NO | Stage: UI shell | Blocks: 5, 6 | Blocked By: 1, 2, 3

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `web/src/components/viewers/Markdown.vue:55-106` - 已支持 code highlight、anchor、toc、KaTeX；无需新 renderer。
  - Pattern: `web/src/components/viewers/Markdown.vue:236-305` - 现有锚点滚动与渲染更新行为。
  - Pattern: `web/src/components/viewers/Markdown.vue:308-355` - 标题、滚动锚点、排版基础样式。
  - Pattern: `web/src/views/UserManagement.vue:14-71` - 基于 route 状态切换内容的可参考思路。
  - Pattern: `web/src/router/index.ts:5-63` - 顶层页面组件挂载方式。
  - API/Type: `web/package.json:6-27` - 当前前端依赖与构建能力；没有额外 docs 框架。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `ApiDocsView.vue` 从 manifest 读取 section 信息与 markdown loader，不存在第二份手写 section 数组。
  - [ ] `/api-docs/<合法section>` 能渲染对应 Markdown；非法 section 会自动跳回 `/api-docs/overview`。
  - [ ] 页面核心节点均带稳定 `data-testid`，便于后续 Playwright 校验。

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Docs view renders selected markdown section
    Tool: Playwright
    Steps: 启动前后端；访问 `http://127.0.0.1:5173/api-docs/overview`；等待 `[data-testid="api-docs-page"]`；确认 `[data-testid="api-docs-title"]` 可见，且 `[data-testid="api-docs-content"]` 内包含 overview 首屏标题文本。
    Expected: 页面成功渲染 overview 文档，没有空白态或报错态。
    Evidence: .sisyphus/evidence/task-4-api-docs-overview.png

  Scenario: Invalid docs section redirects safely
    Tool: Playwright
    Steps: 访问 `http://127.0.0.1:5173/api-docs/not-a-real-section`；等待导航完成；读取当前 URL 与 `[data-testid="api-docs-title"]`。
    Expected: URL 最终为 `/api-docs/overview`，标题显示 overview 文档标题。
    Evidence: .sisyphus/evidence/task-4-api-docs-invalid-route.txt
  ```

  **Commit**: NO | Message: `feat(web): add api docs reader view` | Files: `web/src/views/ApiDocsView.vue`

- [ ] 5. 打通路由、侧边栏入口与文档态导航行为

  **What to do**: 在 `web/src/router/index.ts` 注册 `/api-docs` → `/api-docs/overview` 重定向，以及 `/api-docs/:section` 实际阅读路由。更新 `web/src/components/AppSidebar.vue`：在非文档态时把原先禁用的 `API文档` 入口改为真实跳转；在文档态（`route.path.startsWith('/api-docs')`）时，侧边栏切换为由 manifest 驱动的文档 section 分组，并对当前 section 高亮。更新 `web/src/App.vue`：让 `/api-docs*` 与 `/users` 一样在桌面宽度默认展开侧边栏、在移动端默认收起。所有文档侧边栏项都加 `data-testid="api-docs-sidebar-item-<slug>"`。
  **Must NOT do**: 不要继续保留 `disabled: true`；不要把文档导航复制成第三份常量；不要让 docs route 需要登录；不要让 `/api-docs` 进入后侧边栏继续显示旧的占位说明文案。

  **Recommended Agent Profile**:
  - Category: `unspecified-low` - Reason: 主要是路由与壳层状态整合，逻辑清晰、风险较低。
  - Skills: `[]` - 不需要额外技能。
  - Omitted: [`frontend-design`] - 这里重点是行为正确，不是视觉创新。

  **Parallelization**: Can Parallel: NO | Stage: integration | Blocks: 6 | Blocked By: 1, 4

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `web/src/router/index.ts:5-63` - 现有页面路由注册与 `meta` 结构。
  - Pattern: `web/src/App.vue:33-54,61-80` - 现有 `syncAppSidebarForRoute()` 与桌面断点联动逻辑。
  - Pattern: `web/src/components/AppSidebar.vue:87-100` - 当前 API 文档占位入口位置。
  - Pattern: `web/src/components/AppSidebar.vue:131-154,188-203` - 侧边栏按 route 切换 section 与点击行为的现有写法。
  - Pattern: `web/src/components/users/navigation.ts:61-84` - 分组导航生成方式，可直接类比 docs 分组。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `/api-docs` 会重定向到 `/api-docs/overview`。
  - [ ] 首页侧边栏中的 `API文档` 入口可点击并进入文档区。
  - [ ] 当位于 `/api-docs/*` 时，侧边栏显示 docs 分组而不是旧的占位 section，当前 section 具有 active 状态。

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Sidebar entry opens docs landing route
    Tool: Playwright
    Steps: 设置视口宽度 1280；访问 `http://127.0.0.1:5173/`；点击侧边栏中的 `[data-testid="api-docs-sidebar-entry"]`（若你用不同 testid，保证计划内一致）；等待路由变化。
    Expected: URL 变为 `/api-docs/overview`，且文档页面可见。
    Evidence: .sisyphus/evidence/task-5-sidebar-entry.png

  Scenario: Deep-link refresh preserves docs section
    Tool: Playwright
    Steps: 直接访问 `http://127.0.0.1:5173/api-docs/files`；等待 `[data-testid="api-docs-sidebar-item-files"]` 出现；刷新页面一次。
    Expected: 刷新后仍停留在 `/api-docs/files`，files 项保持 active，正文标题为 files 文档标题。
    Evidence: .sisyphus/evidence/task-5-deeplink-refresh.txt
  ```

  **Commit**: NO | Message: `feat(web): wire api docs routes and sidebar` | Files: `web/src/router/index.ts`, `web/src/components/AppSidebar.vue`, `web/src/App.vue`

- [ ] 6. 完成文档体验抛光、原始参考链接与范围校验

  **What to do**: 打磨最终用户体验，使文档阅读页在桌面/移动端都可读。具体包括：在 overview 或统一页头中放置“原始参考链接”卡片（链接到 `/docs`、`/redoc`、`/openapi.json`，仅作辅助参考）；确保本地导航、TOC、长代码块、长表格在窄屏下可滚动；必要时为 docs 页面增加局部样式容器，但不要破坏通用 `Markdown.vue`。同时做一轮内容范围清洗：确保排除模块不出现在正文，确保常用公开 API 均被覆盖，确保没有任何运行时请求 `/docs`、`/redoc`、`/openapi.json` 才能显示主体内容。若需要辅助组件（如 `ApiDocsReferenceLinks.vue`），在这一任务完成。
  **Must NOT do**: 不要让页面加载正文时依赖后端 docs 接口；不要加入搜索、复制 SDK、Try it out、版本切换；不要把参考链接伪装成正文主入口。

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - Reason: 任务包含可读性抛光、响应式与交互可感知质量。
  - Skills: [`frontend-design`] - 需要更好的文档阅读观感与信息层级。
  - Omitted: [`web-design-guidelines`] - 当前目标是落地实现，不是审计式 review。

  **Parallelization**: Can Parallel: NO | Stage: polish | Blocks: Final Verification Wave | Blocked By: 1, 2, 3, 4, 5

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `web/src/components/viewers/Markdown.vue:95-106,236-355` - 现有 TOC、锚点和平滑滚动能力，可直接利用。
  - Pattern: `README.md:66-70` - 原始 `/docs`、`/redoc`、健康接口的项目说明。
  - API/Type: `main.py:96-104` - 根路径已把 `/docs` 作为官方原始文档入口之一。
  - API/Type: `app/core/middleware/install_gate.py:19-26` - `/docs`、`/redoc`、`/openapi.json` 在安装态也可访问，适合作为参考链接。
  - API/Type: `app/core/dependencies.py:83-168` - 检查正文是否正确解释不同鉴权模型。

  **Acceptance Criteria** (agent-executable only):
  - [ ] 文档页存在“原始参考链接”区域，但正文首屏主体依旧是手写 Markdown 内容。
  - [ ] 在 390px 宽度下，长代码块和表格不会把整个页面撑坏；正文区域可水平滚动或布局自适应。
  - [ ] 页面初始加载时不会自动请求 `/docs`、`/redoc`、`/openapi.json`。
  - [ ] 所有文档正文中不出现 `/api/internal/`、`/api/install`、`/api/user/history/*`、`POST /api/users/refresh`、`POST /api/users/logout`、`GET /api/users/{user_id}/sessions`、`DELETE /api/users/{user_id}/sessions/others`。

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Docs page stays self-contained on first render
    Tool: Playwright
    Steps: 清空网络记录；访问 `http://127.0.0.1:5173/api-docs/overview`；抓取网络请求列表并筛选 `/docs|/redoc|/openapi.json`。
    Expected: 初始渲染阶段对这三类 URL 的请求数为 0；只有用户显式点击原始参考链接后才允许打开。
    Evidence: .sisyphus/evidence/task-6-network-self-contained.txt

  Scenario: Mobile-width docs remain usable
    Tool: Playwright
    Steps: 将视口设为 390x844；访问 `http://127.0.0.1:5173/api-docs/pastes-files`；确认 `[data-testid="api-docs-local-nav"]` 可用；滚动到包含代码块或表格的区域并截图。
    Expected: 页面无明显横向溢出破版，本地导航可点击，代码块/表格区域可读。
    Evidence: .sisyphus/evidence/task-6-mobile-docs.png
  ```

  **Commit**: NO | Message: `feat(web): polish api docs experience` | Files: `web/src/views/ApiDocsView.vue`, `web/src/components/docs/*`, `web/src/content/api-docs/*.md`

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright if UI)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Only create commits if the user explicitly asks for them.
- If asked, prefer a single final commit after F1-F4 approval:
  - `feat(web): add handwritten API docs section`

## Success Criteria
- 首页侧边栏里的 `API文档` 不再是禁用占位项。
- `/api-docs/overview` 成为稳定、可直达、可刷新、可在移动端查看的文档入口。
- 文档正文清楚解释 **API Key 可访问接口** 的用途、参数、认证方式、错误情形与调用示例。
- “哪些接口支持 / 可选支持 / 不支持 API Key” 被明确写死在计划与正文中，而不是由实现者临场判断。
- “哪些接口支持 API Key 访问” 被作为独立事实矩阵写清楚，并与 `get_current_user` / `get_current_user_and_session` / `get_current_user_with_key` / `get_optional_user` 的实现保持一致。
- 文档内容与当前后端实现一致，且没有误导性覆盖到被排除的模块。
