# OpenHarness Enterprise - API Protocol

> 本文档定义后端网关对外暴露的完整 HTTP API 契约。
> 前端开发参见 [frontend-require.md](frontend-require.md)，后端实现参见 [require.md](require.md)。
> **前后端均需严格按照本文档定义开发，任何接口变更必须同步更新本文档。**

---

## 1. 基础约定

### 1.1 Base URL

- **网关地址**：`{GATEWAY_URL}`
- **API 前缀**：`/api/v1`
- **健康检查**：`GET /health`（无需认证）
- **API 文档**：`GET /docs`（Swagger UI，仅开发环境开放）

### 1.2 认证

- **认证方式**：Bearer Token（JWT）
- **请求头**：`Authorization: Bearer <jwt-token>`
- **获取 Token**：通过 `POST /api/v1/auth/login` 用 API Key 换取
- **Token 有效期**：默认 24 小时，可通过 `POST /api/v1/auth/refresh` 续期
- **内部服务间调用**：使用 `X-Internal-Call: true` + `X-Request-ID` + `X-Tenant-ID` + `X-User-ID` 头，跳过网关鉴权

### 1.3 版本管理

- URL 前缀 `/api/v1/` 表示版本号，支持多版本共存
- 新版本上线后旧版本保留至少一个迭代周期
- 弃用接口返回 `410 Gone` + `code: "API_DEPRECATED"`

### 1.4 分页

所有列表接口统一使用以下分页约定：

- **请求参数**：`page`（页码，从 1 开始）+ `page_size`（每页条数，默认 20，最大 100）
- **响应结构**：

```json
{
  "items": [],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

### 1.5 筛选与排序

- 列表筛选统一使用 query string：`?status=running&name=xxx&created_after=2026-04-01`
- 时间范围使用 `_after` / `_before` 后缀（ISO 8601 格式）：`?created_after=2026-04-01T00:00:00Z`
- 排序使用 `sort_by` + `sort_order`：`?sort_by=created_at&sort_order=desc`

### 1.6 流式响应

Agent 交互支持 WebSocket 流式通道：

- **端点**：`ws://{GATEWAY_URL}/api/v1/agents/{id}/stream`
- **协议**：与 SDK 的 `StreamEvent` 对齐，JSON 帧格式
- **认证**：通过 URL query 参数 `?token=<jwt-token>` 传递

---

## 2. 统一响应格式

### 2.1 成功响应

单条数据：

```json
{
  "data": { ... }
}
```

列表数据：

```json
{
  "items": [],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

操作结果：

```json
{
  "ok": true,
  "task_id": "task-uuid"  // 异步任务时返回
}
```

### 2.2 错误响应

所有错误返回统一结构：

```json
{
  "code": "QUOTA_EXCEEDED",
  "message": "Organization agent quota exceeded",
  "request_id": "req-uuid",
  "details": { "quota": 10, "current": 10 }
}
```

- `code`：机器可读错误码（大写蛇形），前端用于错误映射
- `message`：人类可读错误描述
- `request_id`：请求唯一标识，贯穿全链路，用于问题排查
- `details`：可选，携带错误上下文（如校验失败的字段信息）

### 2.3 错误码表

| HTTP Status | code | 说明 | details 结构 |
|---|---|---|---|
| 401 | `UNAUTHORIZED` | 未认证或 Token 无效/过期 | - |
| 403 | `FORBIDDEN` | 无权限访问该资源 | `{ "required_role": "admin" }` |
| 403 | `QUOTA_EXCEEDED` | 超出配额上限 | `{ "quota": 10, "current": 10 }` |
| 404 | `NOT_FOUND` | 资源不存在 | `{ "resource": "agent", "id": "xxx" }` |
| 409 | `CONFLICT` | 资源冲突（如名称重复） | `{ "field": "name" }` |
| 410 | `API_DEPRECATED` | 接口已弃用 | `{ "migration": "Use POST /api/v2/..." }` |
| 422 | `VALIDATION_ERROR` | 请求参数校验失败 | `{ "fields": { "name": "required", "email": "invalid format" } }` |
| 429 | `RATE_LIMITED` | 请求频率超限 | `{ "retry_after": 30 }` |
| 500 | `INTERNAL_ERROR` | 服务端内部错误 | - |
| 502 | `UPSTREAM_UNAVAILABLE` | 下游服务不可用 | `{ "service": "host" }` |
| 503 | `SERVICE_UNAVAILABLE` | 服务暂时不可用（熔断/维护） | `{ "retry_after": 60 }` |

---

## 3. 路由表

### 3.1 网关路由映射

| 路径前缀 | 后端目标服务 | 说明 |
|---|---|---|
| `/api/v1/auth/*` | 权限管理服务（认证子模块） | 登录、Token 刷新、登出 |
| `/api/v1/agents/*` | 中央调度 → Agent 宿主服务 | 实例 CRUD、操控、记忆同步、流式交互 |
| `/api/v1/memory/*` | 中央调度 → 记忆服务 | 资产存储与检索 |
| `/api/v1/market/*` | 中央调度 → 市场服务 | 模板、Skill、MCP、Agent 配置浏览与订阅 |
| `/api/v1/builder/*` | 中央调度 → 市场服务 | Agent 定制构建（创建/编辑/发布 Agent 配置） |
| `/api/v1/org/*` | 中央调度 → 权限管理服务 | 组织、用户、API Key 管理 |
| `/api/v1/billing/*` | 中央调度 → 计费引擎 | 费用查询、账单导出、预算管理 |
| `/api/v1/tasks/*` | 中央调度 → Celery | 异步任务状态查询 |
| `/api/v1/approvals/*` | 中央调度 → 审批模块 | 审批列表与操作 |
| `/health` | 网关自身 | 健康检查 |

### 3.2 内部服务间路由

各微服务暴露 `/internal/*` 前缀的内部接口，仅供中央调度服务调用，不经过网关。

---

## 4. 接口定义

### 4.1 认证

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|---|---|---|---|---|
| POST | `/api/v1/auth/login` | API Key 登录 | `{ "api_key": "oh-org-xxx" }` | `{ "token": "jwt...", "expires_at": "ISO8601", "refresh_token": "...", "user": { "id", "name", "role", "org_id", "permissions" } }` |
| POST | `/api/v1/auth/refresh` | Token 续期 | `{ "refresh_token": "..." }` | `{ "token": "jwt...", "expires_at": "ISO8601" }` |
| POST | `/api/v1/auth/logout` | 登出 | - | `{ "ok": true }` |
| GET | `/api/v1/auth/me` | 获取当前用户信息 | - | `{ "id", "name", "role", "org_id", "permissions" }` |

### 4.2 Agent 实例

| 方法 | 路径 | 说明 | 请求体 / 参数 | 响应 |
|---|---|---|---|---|
| GET | `/api/v1/agents` | 实例列表 | `?page&page_size&status&name&created_after` | 分页响应，items 含 `{ id, guid, name, status, host_node, model, created_at, last_active_at }` |
| POST | `/api/v1/agents` | 创建实例 | `{ "name", "template_id"?, "agent_config_id"?, "model", "config" }` | `{ "id", "guid", "status": "creating", "task_id" }` |
| GET | `/api/v1/agents/{id}` | 实例详情 | - | `{ id, guid, name, status, host_node, model, config, created_at, last_active_at }` |
| DELETE | `/api/v1/agents/{id}` | 销毁实例 | - | `{ "ok": true }` |
| POST | `/api/v1/agents/{id}/restart` | 重启实例 | - | `{ "ok": true, "task_id" }` |
| POST | `/api/v1/agents/batch-restart` | 批量重启 | `{ "ids": [] }` | `{ "ok": true, "task_id" }` |
| POST | `/api/v1/agents/batch-destroy` | 批量销毁 | `{ "ids": [] }` | `{ "ok": true, "task_id" }` |
| POST | `/api/v1/agents/{id}/message` | 发送消息 | `{ "prompt", "stream"?: true }` | 同步返回或 SSE 流式 |
| WS | `/api/v1/agents/{id}/stream` | 流式交互 | `?token=<jwt>` | WebSocket StreamEvent |
| POST | `/api/v1/agents/{id}/command` | 执行命令 | `{ "command" }` | `{ "output" }` |
| POST | `/api/v1/agents/{id}/skills` | 安装 Skill | `{ "skill_id" }` | `{ "ok": true }` |
| POST | `/api/v1/agents/{id}/mcp` | 配置 MCP | `{ "name", "transport": "stdio"|"http"|"ws", "config" }` | `{ "ok": true }` |
| PUT | `/api/v1/agents/{id}/config` | 修改配置 | `{ "system_prompt"?, "permission_mode"?, "model"? }` | `{ "ok": true }` |
| GET | `/api/v1/agents/{id}/monitor` | 监控数据 | - | `{ "cpu_percent", "memory_mb", "total_tokens" }` |
| GET | `/api/v1/agents/{id}/memory/tree` | 记忆文件树 | - | `{ "paths": [], "tree": {} }` |
| POST | `/api/v1/agents/{id}/memory/upload` | 上传记忆 | `multipart/form-data` | `{ "ok": true }` |
| GET | `/api/v1/agents/{id}/memory/download` | 下载记忆 | - | 文件流 |

**实例状态枚举**：`creating` → `running` → `seeding` → `ready` → `stopping` → `stopped` → `failed`

### 4.3 Agent 定制构建

面向用户的智能体配置编辑与发布接口。

#### 4.3.1 AgentConfig 数据模型

一个完整的 Agent 配置包含以下可定制维度：

```json
{
  "id": "cfg-uuid",
  "name": "Python Code Reviewer",
  "description": "When to use this agent",
  "version": "1.0.0",
  "author_id": "user-uuid",
  "org_id": "org-uuid",
  "visibility": "private",

  "personality": {
    "system_prompt": "You are a senior Python developer...",
    "critical_reminder": "Always check type hints before reviewing",
    "initial_prompt": "Start by reading the project structure",
    "tone": "professional",
    "language": "zh-CN"
  },

  "model": {
    "provider": "litellm",
    "litellm_params": {
      "model": "openai/gpt-4o",
      "api_base": "https://api.openai.com/v1",
      "api_key": "",
      "temperature": 0.7,
      "max_tokens": 4096,
      "top_p": 1.0,
      "frequency_penalty": 0.0,
      "presence_penalty": 0.0,
      "num_ctx": null,
      "drop_params": false,
      "custom_llm_provider": null,
      "timeout": null,
      "max_retries": 2,
      "extra_headers": {}
    }
  },

  "tools": {
    "allowed": ["Read", "Grep", "Glob", "LS", "Bash"],
    "disallowed": ["file_write"]
  },

  "skills": ["search", "debug", "code-review"],

  "mcp_servers": [
    {
      "name": "github",
      "transport": "http",
      "url": "http://localhost:3000/mcp",
      "headers": {}
    }
  ],

  "workspace": {
    "enabled": true,
    "preload_paths": [
      {
        "source": "memory",
        "path": "org-001/workspaces/review-guidelines/"
      },
      {
        "source": "embedded",
        "filename": "code-review-checklist.md",
        "content": "- Check naming conventions\n- Verify type hints\n..."
      },
      {
        "source": "url",
        "url": "https://docs.example.com/internal-guidelines.md"
      }
    ]
  },

  "permissions": {
    "mode": "default",
    "max_turns": 50
  },

  "appearance": {
    "color": "cyan",
    "icon": "code"
  },

  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

**各字段说明**：

| 维度 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 基本信息 | `name` | string | Agent 名称，唯一标识 |
| | `description` | string | 使用场景描述（when to use） |
| | `visibility` | `"private"` \| `"org"` \| `"public"` | 可见性 |
| 性格/人设 | `personality.system_prompt` | string | 完整系统提示词 |
| | `personality.critical_reminder` | string | 每轮注入的短提醒 |
| | `personality.initial_prompt` | string | 首轮前置消息 |
| | `personality.tone` | string | 语气风格标签 |
| | `personality.language` | string | 默认语言 |
| 模型 | `model.provider` | string | 模型提供商，目前仅支持 `litellm` |
| | `model.litellm_params.model` | string | LiteLLM 模型标识（如 `openai/gpt-4o`、`anthropic/claude-3-5-sonnet`、`ollama/qwen2.5-coder`） |
| | `model.litellm_params.api_base` | string \| null | 自定义 API 端点（覆盖默认） |
| | `model.litellm_params.api_key` | string \| null | API Key（敏感字段，存储时加密，前端仅展示掩码） |
| | `model.litellm_params.temperature` | number | 采样温度（0.0-2.0，默认 0.7） |
| | `model.litellm_params.max_tokens` | number | 最大输出 token 数（默认 4096） |
| | `model.litellm_params.top_p` | number | Top-P 采样（0.0-1.0，默认 1.0） |
| | `model.litellm_params.frequency_penalty` | number | 频率惩罚（-2.0-2.0，默认 0.0） |
| | `model.litellm_params.presence_penalty` | number | 存在惩罚（-2.0-2.0，默认 0.0） |
| | `model.litellm_params.num_ctx` | number \| null | 上下文窗口大小（覆盖模型默认值） |
| | `model.litellm_params.drop_params` | boolean | 是否丢弃不支持的参数（默认 false） |
| | `model.litellm_params.custom_llm_provider` | string \| null | 自定义 LLM 提供商标识 |
| | `model.litellm_params.timeout` | number \| null | 请求超时秒数 |
| | `model.litellm_params.max_retries` | number | 重试次数（默认 2） |
| | `model.litellm_params.extra_headers` | object | 额外请求头 |
| 工具 | `tools.allowed` | string[] | 允许使用的工具列表，null=全部 |
| | `tools.disallowed` | string[] | 禁止使用的工具列表 |
| 技能 | `skills` | string[] | 启用的 Skill 名称列表 |
| MCP | `mcp_servers` | object[] | MCP Server 配置列表 |
| 工作空间 | `workspace.enabled` | boolean | 是否启用工作空间预加载 |
| | `workspace.preload_paths` | object[] | 预加载资源列表，支持三种来源 |
| | `workspace.preload_paths[].source` | string | 资源来源：`memory`（记忆服务路径）/ `embedded`（内嵌内容）/ `url`（远程 URL） |
| | `workspace.preload_paths[].path` | string | 记忆服务中的路径（source=memory 时） |
| | `workspace.preload_paths[].filename` | string | 文件名（source=embedded 时） |
| | `workspace.preload_paths[].content` | string | 文件内容（source=embedded 时） |
| | `workspace.preload_paths[].url` | string | 远程 URL（source=url 时） |
| 权限 | `permissions.mode` | string | `default`/`plan`/`acceptEdits`/`bypassPermissions` |
| | `permissions.max_turns` | int | 最大 agentic 轮次 |
| 外观 | `appearance.color` | string | 主题色标识 |
| | `appearance.icon` | string | 图标标识 |

#### 4.3.2 Agent 构建接口

| 方法 | 路径 | 说明 | 请求体 / 参数 | 响应 |
|---|---|---|---|---|
| GET | `/api/v1/builder/configs` | 我的 Agent 配置列表 | `?page&page_size&visibility&keyword` | 分页响应 |
| GET | `/api/v1/builder/configs/{id}` | 获取配置详情 | - | AgentConfig 对象（见 4.3.1） |
| POST | `/api/v1/builder/configs` | 创建 Agent 配置 | AgentConfig（不含 id/created_at/updated_at） | `{ "id", "version": "1.0.0" }` |
| PUT | `/api/v1/builder/configs/{id}` | 更新 Agent 配置 | AgentConfig 部分字段（PATCH 语义） | `{ "ok": true, "version": "1.0.1" }` |
| DELETE | `/api/v1/builder/configs/{id}` | 删除 Agent 配置 | - | `{ "ok": true }` |
| POST | `/api/v1/builder/configs/{id}/publish` | 发布到市场 | `{ "visibility": "org"|"public", "category"?, "tags"? }` | `{ "ok": true, "template_id": "tpl-uuid" }` |
| POST | `/api/v1/builder/configs/{id}/duplicate` | 复制配置 | `{ "name" }` | `{ "id": "new-uuid" }` |
| GET | `/api/v1/builder/configs/{id}/versions` | 版本历史 | `?page&page_size` | 分页响应，items 含 `{ version, changelog, created_at }` |
| POST | `/api/v1/builder/configs/{id}/preview` | 预览配置效果 | AgentConfig | `{ "preview_id", "expires_at" }` |
| POST | `/api/v1/builder/configs/validate` | 校验配置合法性 | AgentConfig | `{ "valid": true, "warnings": [], "errors": [] }` |
| POST | `/api/v1/builder/configs/import` | 导入配置 | `{ "source": "file"|"url", "content" }` | AgentConfig 对象 |
| GET | `/api/v1/builder/configs/{id}/export` | 导出配置 | `?format=yaml|json` | 文件内容（Agent 配置 .md 格式或 JSON） |

### 4.4 市场

| 方法 | 路径 | 说明 | 参数 | 响应 |
|---|---|---|---|---|
| GET | `/api/v1/market/templates` | 模板列表 | `?category&keyword&page&page_size` | 分页响应 |
| GET | `/api/v1/market/templates/{id}` | 模板详情 | - | `{ "id", "name", "description", "category", "scenario", "skills": [], "mcp": [], "resource_spec", "usage_count" }` |
| GET | `/api/v1/market/skills` | Skill 列表 | `?keyword&page&page_size` | 分页响应 |
| GET | `/api/v1/market/skills/{id}` | Skill 详情 | - | `{ "id", "name", "description", "author", "version", "package_url" }` |
| GET | `/api/v1/market/mcps` | MCP 列表 | `?keyword&page&page_size` | 分页响应 |
| GET | `/api/v1/market/mcps/{id}` | MCP 详情 | - | `{ "id", "name", "transport", "description", "config_template" }` |
| GET | `/api/v1/market/categories` | 分类列表 | - | `{ "items": [{ "id", "name", "icon" }] }` |

**模板分类**：`code_development` | `data_analysis` | `ops_automation` | `general_assistant`

### 4.5 计费

| 方法 | 路径 | 说明 | 参数 | 响应 |
|---|---|---|---|---|
| GET | `/api/v1/billing/summary` | 费用概览 | `?period=month` | `{ "total_tokens", "total_cost", "budget", "budget_remaining", "by_instance": [], "by_model": [], "daily_trend": [] }` |
| GET | `/api/v1/billing/records` | 账单明细 | `?page&page_size&instance_id&model&start_date&end_date` | 分页响应，items 含 `{ "time", "instance_name", "model", "input_tokens", "output_tokens", "cost" }` |
| GET | `/api/v1/billing/export` | 导出账单 | `?start_date&end_date&format=csv` | 文件流 |
| GET | `/api/v1/billing/budget` | 查看预算 | `?org_id` | `{ "threshold", "alert_rules": [] }` |
| PUT | `/api/v1/billing/budget` | 设置预算 | `{ "threshold", "alert_rules" }` | `{ "ok": true }` |

### 4.6 组织与权限

| 方法 | 路径 | 说明 | 请求体 / 参数 | 响应 |
|---|---|---|---|---|
| GET | `/api/v1/org/tree` | 组织架构树 | `?depth=3` | `{ "id", "name", "children": [] }` |
| GET | `/api/v1/org/{id}` | 组织详情 | - | `{ "id", "name", "parent_id", "quota", "member_count" }` |
| POST | `/api/v1/org` | 创建子组织 | `{ "name", "parent_id", "quota" }` | `{ "id", "name" }` |
| GET | `/api/v1/org/{id}/members` | 成员列表 | `?page&page_size&role` | 分页响应 |
| POST | `/api/v1/org/{id}/members` | 添加成员 | `{ "user_id", "role" }` | `{ "ok": true }` |
| DELETE | `/api/v1/org/{id}/members/{user_id}` | 移除成员 | - | `{ "ok": true }` |
| PUT | `/api/v1/org/{id}/members/{user_id}` | 修改角色 | `{ "role" }` | `{ "ok": true }` |
| GET | `/api/v1/org/{id}/api-keys` | API Key 列表 | `?page&page_size` | 分页响应，items 含 `{ "id", "label", "user_id", "permissions", "created_at", "expires_at", "last_used_at" }` |
| POST | `/api/v1/org/{id}/api-keys` | 创建 API Key | `{ "label", "permissions", "expires_in_days" }` | `{ "id", "api_key", "expires_at" }` |
| DELETE | `/api/v1/org/{id}/api-keys/{key_id}` | 吊销 API Key | - | `{ "ok": true }` |
| POST | `/api/v1/org/{id}/api-keys/{key_id}/renew` | 续期 | `{ "expires_in_days" }` | `{ "expires_at" }` |
| GET | `/api/v1/permissions` | 权限定义列表（超管） | - | `{ "items": [{ "id", "name", "description" }] }` |
| GET | `/api/v1/roles` | 角色列表（超管） | - | `{ "items": [{ "id", "name", "permissions" }] }` |
| PUT | `/api/v1/roles/{id}` | 修改角色权限（超管） | `{ "permissions" }` | `{ "ok": true }` |

### 4.7 审批

| 方法 | 路径 | 说明 | 参数 | 响应 |
|---|---|---|---|---|
| GET | `/api/v1/approvals` | 审批列表 | `?status=pending&page&page_size` | 分页响应，items 含 `{ "id", "applicant", "applicant_name", "created_at", "template_name", "config_summary", "reason", "status" }` |
| POST | `/api/v1/approvals/{id}/approve` | 通过审批 | - | `{ "ok": true, "task_id" }` |
| POST | `/api/v1/approvals/{id}/reject` | 驳回审批 | `{ "reason" }` | `{ "ok": true }` |
| GET | `/api/v1/approvals/history` | 审批历史 | `?page&page_size&status&date_from&date_to` | 分页响应 |

### 4.8 记忆资产

| 方法 | 路径 | 说明 | 参数 | 响应 |
|---|---|---|---|---|
| GET | `/api/v1/memory/assets` | 资产列表（文件树） | `?path=&recursive=true` | `{ "items": [{ "path", "name", "type": "file|dir", "size", "updated_at" }] }` |
| GET | `/api/v1/memory/assets/{path}` | 获取资产内容 | - | 文件内容或文件流 |
| PUT | `/api/v1/memory/assets/{path}` | 上传资产 | `multipart/form-data` | `{ "ok": true }` |
| DELETE | `/api/v1/memory/assets/{path}` | 删除资产 | - | `{ "ok": true }` |
| GET | `/api/v1/memory/search` | 搜索资产 | `?keyword&page&page_size` | 分页响应 |

### 4.9 异步任务

| 方法 | 路径 | 说明 | 响应 |
|---|---|---|---|
| GET | `/api/v1/tasks/{task_id}` | 查询任务状态 | `{ "id", "status": "pending|running|completed|failed", "result"?, "error"? }` |

---

## 5. 数据模型枚举

### 5.1 实例状态

| 值 | 说明 |
|---|---|
| `creating` | 正在创建 |
| `running` | 运行中（容器已启动） |
| `seeding` | 正在初始化（安装 Skill/MCP/记忆） |
| `ready` | 就绪（可交互） |
| `stopping` | 正在停止 |
| `stopped` | 已停止 |
| `failed` | 创建或运行失败 |

### 5.2 权限模式

| 值 | 说明 |
|---|---|
| `default` | 默认模式，危险操作需确认 |
| `plan` | 规划模式，只读 + 提出建议 |
| `acceptEdits` | 自动接受文件编辑 |
| `bypassPermissions` | 跳过所有权限检查（最高权限） |

### 5.3 模型配置

模型通过 LiteLLM 统一代理，`model.litellm_params.model` 字段使用 LiteLLM 的模型标识格式：`{provider}/{model_name}`。常用示例：

| LiteLLM 标识 | 提供商 | 说明 |
|---|---|---|
| `openai/gpt-4o` | OpenAI | GPT-4o |
| `openai/gpt-4o-mini` | OpenAI | GPT-4o Mini |
| `anthropic/claude-3-5-sonnet-20241022` | Anthropic | Claude 3.5 Sonnet |
| `anthropic/claude-3-5-haiku-20241022` | Anthropic | Claude 3.5 Haiku |
| `ollama/qwen2.5-coder:32b` | Ollama | 本地 Qwen2.5 Coder |
| `ollama/deepseek-coder-v2:latest` | Ollama | 本地 DeepSeek Coder |
| `azure/gpt-4o` | Azure OpenAI | Azure 托管的 GPT-4o |
| `openai/{自定义模型名}` + `api_base` | 自定义 | 任意 OpenAI 兼容 API |

完整的提供商列表和参数参见 [LiteLLM 文档](https://docs.litellm.ai/)。`api_base` 字段可覆盖默认端点，用于对接私有化部署的模型服务。

### 5.4 MCP 传输协议

| 值 | 说明 |
|---|---|
| `stdio` | 标准输入输出，本地进程 |
| `http` | HTTP/SSE 远程服务 |
| `ws` | WebSocket 远程服务 |

### 5.5 Agent 可见性

| 值 | 说明 |
|---|---|
| `private` | 仅创建者可见 |
| `org` | 组织内可见 |
| `public` | 全平台可见（市场公开） |

---

## 6. 变更日志

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-04-16 | v1.0.0 | 初始版本，定义全部接口 |
