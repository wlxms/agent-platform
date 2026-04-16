# OpenHarness Enterprise - Frontend Requirements

> 本文档定义前端管理控制台的需求，仅依赖后端网关暴露的 HTTP API 契约。
> API 接口的完整定义参见 [api-protocol.md](api-protocol.md)，后端实现参见 [require.md](require.md)。
> **前端开发必须严格按照 api-protocol.md 定定的接口契约实现，不得自行约定。**

---

## 1. 技术选型

- 框架：React + TypeScript
- 状态管理：Zustand（轻量，避免 Redux 过度设计）
- UI 组件库：Ant Design 5.x（企业级组件丰富，Table/Form/ProComponents 覆盖后台高频场景）
- 路由：React Router v6
- HTTP 客户端：Axios（拦截器统一处理认证与错误）
- 图表：ECharts（费用趋势、资源使用率等可视化）
- 构建工具：Vite

---

## 2. 角色与权限

| 角色 | 可访问页面 |
|---|---|
| 超级管理员 | 全部页面，包括组织管理、系统配置、全局计费、审批管理 |
| 组织管理员 | 本组织及下级组织的管理、用户管理、计费概览、审批 |
| 团队管理员 | 本团队成员管理、Agent 实例管理、费用查看、Agent 定制 |
| 普通用户 | 个人 Agent 管理、市场浏览、个人费用、记忆管理、Agent 定制 |

前端根据登录后返回的用户角色，动态渲染可访问的菜单与路由。未授权页面访问重定向到 403 提示页。

---

## 3. API 契约引用

所有 API 接口的定义（路径、方法、请求体、响应结构、错误码）统一在 [api-protocol.md](api-protocol.md) 中维护，前端不额外定义接口约定。

### 3.1 Axios 层对接

```typescript
// src/api/client.ts
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_GATEWAY_URL + '/api/v1',
  headers: { 'Authorization': `Bearer ${getToken()}` },
});

// 响应拦截器：统一处理错误码（参照 api-protocol.md 2.3 节错误码表）
apiClient.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const { code, message, request_id } = err.response?.data ?? {};
    switch (code) {
      case 'UNAUTHORIZED':     router.navigate('/login'); break;
      case 'FORBIDDEN':         message.warning('无权限访问'); break;
      case 'QUOTA_EXCEEDED':    message.warning('已达到配额上限，请联系管理员'); break;
      case 'RATE_LIMITED':      message.warning('请求过于频繁，请稍后重试'); break;
      case 'VALIDATION_ERROR':  // 表单字段标红处理 details.fields
      default:                  message.error(message || '请求失败');
    }
    // 开发模式底部状态栏显示 request_id
    return Promise.reject(err);
  }
);
```

### 3.2 模块 API 映射

各页面对应的 API 接口速查（完整定义见 [api-protocol.md 第 4 节](api-protocol.md#4-接口定义)）：

| 前端页面 | API 前缀 | 协议文档章节 |
|---|---|---|
| 登录 | `/api/v1/auth/*` | 4.1 认证 |
| 实例管理 | `/api/v1/agents/*` | 4.2 Agent 实例 |
| Agent 定制 | `/api/v1/builder/*` | 4.3 Agent 定制构建 |
| 市场 | `/api/v1/market/*` | 4.4 市场 |
| 计费 | `/api/v1/billing/*` | 4.5 计费 |
| 组织权限 | `/api/v1/org/*` | 4.6 组织与权限 |
| 审批 | `/api/v1/approvals/*` | 4.7 审批 |
| 记忆资产 | `/api/v1/memory/*` | 4.8 记忆资产 |
| 任务状态 | `/api/v1/tasks/*` | 4.9 异步任务 |

---

## 4. 页面模块设计

### 4.1 登录页

- **API Key 登录**：用户输入组织分配的 API Key，调用 `POST /api/v1/auth/login`
- 登录成功后将 JWT Token 存储于 localStorage，跳转到仪表盘
- **Token 自动续期**：Axios 拦截器检测 401 后自动调用 `POST /api/v1/auth/refresh`，刷新失败跳转登录页
- **单点登出**：调用 `POST /api/v1/auth/logout`，清除本地 Token

### 4.2 仪表盘（Dashboard）

根据用户角色展示不同内容，三套仪表盘可在 Tab 或子路由间切换。

#### 4.2.1 个人仪表盘（所有用户）

- 当前用户拥有的 Agent 实例列表（名称、状态、最后活跃时间）
- 快捷操作入口：新建 / 重启 / 销毁
- 最近 7 天个人费用趋势折线图（调用 `GET /api/v1/billing/summary?period=week`）
- API 调用：
  - `GET /api/v1/agents?page_size=10`
  - `GET /api/v1/billing/summary?period=week`

#### 4.2.2 组织仪表盘（组织/团队管理员）

- 组织总实例数 / 运行中 / 闲置分布饼图
- 组织级费用汇总与预算剩余进度条
- 待审批事项数量角标
- API 调用：
  - `GET /api/v1/billing/summary?org_id={org_id}`
  - `GET /api/v1/approvals?status=pending&page_size=1`（获取 count）
  - `GET /api/v1/agents?org_id={org_id}`（统计各状态数量）

#### 4.2.3 系统仪表盘（超级管理员）

- 全局资源使用热力图（按宿主节点）
- 各服务健康状态卡片
- 全局限流 / 熔断实时状态
- API 调用：预留管理端接口，首期可展示静态 mock 数据

### 4.3 Agent 实例管理

#### 4.3.1 实例列表页

- Ant Design ProTable，支持按状态 / 名称 / 创建时间筛选与分页
- 每行显示：实例名、GUID、状态、宿主节点、创建时间、最后活跃时间
- 状态 Badge 颜色映射：`ready`=绿色、`running`=蓝色、`creating/seeding`=黄色、`stopped/failed`=灰色/红色
- 批量操作工具栏：批量重启（`POST /api/v1/agents/batch-restart`）、批量销毁（`POST /api/v1/agents/batch-destroy`）
- API 调用：`GET /api/v1/agents`

#### 4.3.2 实例详情页

以 Tab 或 Card 组布局展示四个面板：

1. **基本信息卡片**：GUID、状态、宿主节点、模型配置、创建时间
   - API：`GET /api/v1/agents/{id}`

2. **操控面板**：
   - Web Terminal 嵌入（`POST /api/v1/agents/{id}/command` 或 WebSocket）
   - 安装 Skill（`POST /api/v1/agents/{id}/skills`）
   - 配置 MCP Server（`POST /api/v1/agents/{id}/mcp`）
   - 修改 System Prompt / 权限模式（`PUT /api/v1/agents/{id}/config`）

3. **记忆同步面板**：
   - 展示记忆文件树（`GET /api/v1/agents/{id}/memory/tree`）
   - 上传（`POST /api/v1/agents/{id}/memory/upload`）
   - 下载（`GET /api/v1/agents/{id}/memory/download`）

4. **监控卡片**：
   - CPU / 内存占用实时折线（`GET /api/v1/agents/{id}/monitor`，轮询 5s）
   - Token 消耗累计

#### 4.3.3 新建实例页

- 表单：选择模板（`GET /api/v1/market/templates` 下拉）或自定义配置
- 填写：名称、选择模型、设置资源规格、配置 Skill / MCP
- 提交调用 `POST /api/v1/agents`，返回 `task_id`，跳转到实例列表并显示创建进度（轮询 `GET /api/v1/tasks/{task_id}`）

### 4.4 Agent 市场

#### 4.4.1 市场首页

- 左侧分类导航（`GET /api/v1/market/categories`）
- 顶部搜索栏（`?keyword=xxx` 模糊搜索）
- 模板卡片网格展示
- API 调用：`GET /api/v1/market/templates?category={id}&keyword={kw}`

#### 4.4.2 模板详情页

- 模板名称、描述、适用场景、预配置的 Skill / MCP 列表、所需资源规格、使用人数统计
- 底部"申领此模板"按钮 → 跳转新建实例页并预填配置
- API 调用：`GET /api/v1/market/templates/{id}`

#### 4.4.3 Skill 商店

- 列表展示（名称、描述、作者、版本），支持搜索
- 支持一键安装到指定 Agent 实例
- API 调用：`GET /api/v1/market/skills`、`POST /api/v1/agents/{id}/skills`

#### 4.4.4 MCP 商店

- 列表展示（名称、传输协议 stdio/http、配置参数模板），支持搜索
- 支持一键配置到指定 Agent 实例
- API 调用：`GET /api/v1/market/mcps`、`POST /api/v1/agents/{id}/mcp`

### 4.5 Agent 定制构建

面向所有用户的智能体开发工作台，类似"智能体工厂"概念，用户可以从零搭建或基于模板微调一个专属 Agent。API 定义参见 [api-protocol.md 4.3 节](api-protocol.md#43-agent-定制构建)。

#### 4.5.1 我的 Agent 列表页

- 展示当前用户创建的所有 Agent 配置，支持按名称/可见性/更新时间筛选
- 每张卡片展示：名称、描述、主题色标识、可见性标签、版本号、更新时间、使用次数
- 操作：编辑、复制、删除、发布到市场、导出
- API 调用：`GET /api/v1/builder/configs`

#### 4.5.2 Agent 编辑器（核心页面）

左侧为配置面板（可折叠的分区），右侧为实时预览区域。编辑器采用自动保存 + 手动保存双模式。

**分区一：基础信息**

- 名称（必填）、描述（必填，"when to use"）
- 可见性选择：私有 / 组织内 / 公开
- 主题色选择（对应 SDK `color` 字段：red/green/blue/yellow/purple/orange/cyan）
- 图标选择

**分区二：性格与人设**

- **System Prompt 编辑器**：Markdown 富文本编辑器（支持实时预览），对应 `personality.system_prompt`
- **Critical Reminder**：单行输入，每轮对话注入的短提醒（如"Always check tests"）
- **Initial Prompt**：单行输入，首轮前置消息
- **语气风格**：下拉选择（professional / friendly / concise / creative）
- **默认语言**：下拉选择（zh-CN / en-US / auto）

**分区三：模型配置**

- **Provider**：固定为 LiteLLM（统一模型代理层）
- **模型标识**：输入框，支持 LiteLLM 格式 `{provider}/{model}`，带输入提示（如输入 `openai/` 自动补全可选模型、输入 `ollama/` 提示本地模型）
- **API Base**：可选，自定义端点 URL（用于私有化部署的模型服务）
- **API Key**：密码输入框，敏感字段仅展示掩码，存储后端加密
- **高级参数**（折叠面板）：
  - Temperature：滑块 0.0-2.0，默认 0.7
  - Max Tokens：数字输入框，默认 4096
  - Top P：滑块 0.0-1.0，默认 1.0
  - Frequency Penalty：滑块 -2.0-2.0，默认 0.0
  - Presence Penalty：滑块 -2.0-2.0，默认 0.0
  - Context Window（num_ctx）：可选，覆盖模型默认上下文长度
  - Timeout：可选，请求超时秒数
  - Max Retries：数字输入框，默认 2
  - Extra Headers：键值对编辑器，添加额外请求头
- 模型配置完整参数参见 [api-protocol.md 5.3 节](api-protocol.md#53-模型配置)

**分区四：工具权限**

- 工具开关面板：展示所有可用工具列表（对应 SDK 40+ tools），每个工具一行带 Toggle
- 支持搜索过滤工具名
- 快捷操作：全选 / 全不选 / 仅读写
- 禁用工具列表（`disallowed_tools`）：独立配置

**分区五：技能配置**

- 已安装 Skill 列表（Tag 样式展示），支持移除
- 从市场安装 Skill：点击"添加 Skill"弹出 Skill 选择器（`GET /api/v1/market/skills`）
- 每个 Skill Tag 显示名称 + 版本，hover 显示描述

**分区六：MCP 配置**

- 已配置的 MCP Server 列表，每项显示名称、传输协议标识（stdio/http/ws）、连接状态
- 新增 MCP Server 弹窗表单：
  - 名称
  - 传输协议选择：stdio / http / ws
  - 根据协议动态渲染配置字段（stdio: command + args + env + cwd；http: url + headers；ws: url + headers）
- 支持"从市场快速添加"（`GET /api/v1/market/mcps`，选择后自动填充配置模板）

**分区七：工作空间（Workspace）**

为远端 HarnessAgent 实例预加载 Asset 资产。创建实例时，这些资源会被注入到 Agent 的工作空间目录中，Agent 启动后即可直接使用（如读取规范文档、参考代码模板等）。

- **开关**：启用/禁用工作空间预加载
- **预加载资源列表**：支持三种来源，每条资源一行，显示来源标识 + 路径/文件名 + 操作按钮
  - **从记忆服务加载**（source=memory）：文件浏览器弹窗，选择记忆服务中的路径（`GET /api/v1/memory/assets`），支持选目录或选文件
  - **内嵌内容**（source=embedded）：标题 + Markdown 编辑器，直接编写文件内容，保存时自动生成文件名
  - **从远程 URL 加载**（source=url）：输入 URL，系统自动拉取内容（创建实例时执行）
- 支持拖拽排序（控制 Agent 加载资源的顺序）
- 资源数据结构参见 [api-protocol.md workspace.preload_paths](api-protocol.md)

**分区八：权限与安全**

- 权限模式：Radio 选择（default / plan / acceptEdits / bypassPermissions），每个选项带说明提示
- 最大 agentic 轮次：数字输入框（0 = 无限制）

**操作栏（底部固定）**：

- 校验配置：`POST /api/v1/builder/configs/validate`，显示校验结果（warnings / errors）
- 预览效果：`POST /api/v1/builder/configs/{id}/preview`，打开预览对话窗口
- 保存草稿：`PUT /api/v1/builder/configs/{id}`
- 发布到市场：`POST /api/v1/builder/configs/{id}/publish`，选择可见性和分类

#### 4.5.3 预览对话窗口

- 基于 Agent 配置创建一个临时沙盒实例（`POST /api/v1/builder/configs/{id}/preview`）
- 嵌入式对话界面：用户输入消息，Agent 根据定制配置回复
- 展示当前使用的模型、System Prompt 摘要、已加载的 Skill/MCP 列表
- 预览实例有效期由后端控制（如 30 分钟），过期自动销毁
- 不计入计费

#### 4.5.4 导入/导出

- 导出：选择格式（YAML / JSON），下载 Agent 配置文件
- 导入：上传文件或粘贴 URL，解析为 AgentConfig，支持校验后导入
- API 调用：`GET /api/v1/builder/configs/{id}/export`、`POST /api/v1/builder/configs/import`

#### 4.5.5 版本历史

- 展示 Agent 配置的版本列表（版本号、更新时间）
- 支持查看历史版本的完整配置
- 支持回滚到指定版本
- API 调用：`GET /api/v1/builder/configs/{id}/versions`

### 4.6 计费与费用

#### 4.6.1 费用概览页

- 当前周期费用汇总卡片（总消耗 Token 数、折算金额、预算剩余）
- 按 Agent 实例的消耗排名柱状图
- 按模型的消耗占比饼图
- 按天的消耗趋势折线图
- API 调用：`GET /api/v1/billing/summary`，使用返回数据渲染 ECharts

#### 4.6.2 账单明细页

- ProTable 展示逐条消耗记录（时间、实例名、模型、input_tokens、output_tokens、折算费用）
- 筛选：按时间范围 / 实例 / 模型
- 导出 CSV（`GET /api/v1/billing/export`）
- API 调用：`GET /api/v1/billing/records`

#### 4.6.3 预算管理页（管理员可见）

- 设置组织 / 团队 / 个人级预算阈值与告警规则
- API 调用：`GET /api/v1/billing/budget`、`PUT /api/v1/billing/budget`

### 4.7 组织与权限管理

#### 4.7.1 组织架构页

- 树形控件展示组织层级（公司 → 部门 → 团队），支持展开 / 折叠 / 点击查看详情
- API 调用：`GET /api/v1/org/tree?depth=3`

#### 4.7.2 成员管理页

- 当前组织节点的成员列表，支持添加 / 移除成员、分配角色
- API 调用：`GET /api/v1/org/{id}/members`、`POST /api/v1/org/{id}/members`、`DELETE /api/v1/org/{id}/members/{user_id}`

#### 4.7.3 API Key 管理页

- 列表展示本组织下签发的所有 API Key（标识、关联用户/组织、权限范围、创建时间、过期时间、最后使用时间）
- 支持创建 / 吊销 / 续期
- API 调用：`GET /api/v1/org/{id}/api-keys`、`POST /api/v1/org/{id}/api-keys`、`DELETE /api/v1/org/{id}/api-keys/{key_id}`

#### 4.7.4 权限配置页（超级管理员可见）

- 自定义权限定义的 CRUD，权限与角色的绑定管理
- API 调用：`GET /api/v1/permissions`、`GET /api/v1/roles`、`PUT /api/v1/roles/{id}`

### 4.8 审批管理

#### 4.8.1 待审批列表

- 表格展示待审批的 Agent 申领请求（申请人、申请时间、模板/配置详情、申请理由）
- 操作：通过 / 驳回（驳回时填写原因）
- API 调用：`GET /api/v1/approvals?status=pending`、`POST /api/v1/approvals/{id}/approve`、`POST /api/v1/approvals/{id}/reject`

#### 4.8.2 审批历史

- 已处理的审批记录，支持按时间 / 状态筛选
- API 调用：`GET /api/v1/approvals/history`

### 4.9 记忆资产管理

#### 4.9.1 资产浏览页

- 文件树形式展示用户在记忆服务中的所有资产
- 支持在线预览文本类文件（.md / .json / .yaml / .txt）
- 支持上传 / 下载 / 删除
- API 调用：`GET /api/v1/memory/assets`、`GET /api/v1/memory/assets/{path}`、`PUT /api/v1/memory/assets/{path}`、`DELETE /api/v1/memory/assets/{path}`

#### 4.9.2 资产搜索页

- 基于关键词搜索记忆服务中的资产内容
- API 调用：`GET /api/v1/memory/search?keyword={kw}`

---

## 5. 全局交互规范

### 5.1 统一错误提示

Axios 响应拦截器捕获统一错误格式（code + message + details），使用 Ant Design `message.error()` 展示。错误码定义与完整映射参见 [api-protocol.md 2.3 节](api-protocol.md#23-错误码表)。

| 错误码 | 前端行为 |
|---|---|
| `UNAUTHORIZED` | 跳转登录页 |
| `FORBIDDEN` | 提示无权限，禁用相关按钮 |
| `QUOTA_EXCEEDED` | 提示"已达到配额上限，请联系管理员" |
| `RATE_LIMITED` | 提示"请求过于频繁，请稍后重试" |
| `NOT_FOUND` | 提示资源不存在 |
| `VALIDATION_ERROR` | 表单字段标红 + 显示 details 中的字段错误 |

### 5.2 加载状态

- 所有数据请求页面使用 Ant Design `Spin` 或骨架屏
- 表格数据加载使用 ProTable 内置 loading
- 提交按钮点击后 loading 状态，防止重复提交

### 5.3 请求 ID 追踪

- 每个请求的 `request_id` 可在页面底部状态栏（开发模式）查看，便于用户反馈问题时提供排查线索

### 5.4 响应式布局

- 最小支持 1280px 宽度，主要适配桌面端浏览器（企业内网场景）

### 5.5 国际化预留

- UI 文本提取为 i18n key，首期仅支持中文，预留英文切换能力

---

## 6. 路由结构

```
/login                          → 登录页（无需认证）
/                               → 重定向到 /dashboard
/dashboard                      → 仪表盘（根据角色展示不同 Tab）
/agents                         → 实例列表
/agents/new                     → 新建实例
/agents/:id                     → 实例详情
/market                         → 市场首页
/market/templates/:id           → 模板详情
/market/skills                  → Skill 商店
/market/mcps                    → MCP 商店
/builder                        → 我的 Agent 列表
/builder/new                    → 创建新 Agent
/builder/:id                    → Agent 编辑器
/builder/:id/preview            → 预览对话窗口
/builder/:id/versions           → 版本历史
/billing                        → 费用概览
/billing/records                → 账单明细
/billing/budget                 → 预算管理（管理员）
/org                            → 组织架构
/org/:id/members                → 成员管理
/org/:id/api-keys               → API Key 管理
/permissions                    → 权限配置（超管）
/approvals                      → 待审批列表
/approvals/history              → 审批历史
/memory                         → 资产浏览
/memory/search                  → 资产搜索
/403                            → 无权限提示
```

路由守卫：未登录重定向 `/login`，角色不匹配重定向 `/403`。
