结合 agent-orchestrator SDK，设计一个可扩展的多进程 Agent 编排平台。框架追求简单但足够灵活：开发阶段单机多进程即可运行，生产阶段可平滑过渡到真实分布式部署。主要目标是企业内部 Agent 申领管理、消耗统计与费用控制。

平台采用 **adapter 模式**：agent-orchestrator SDK 是通用的 Agent 编排引擎，不绑定任何特定的 Agent 运行时。通过可插拔的 Agent Adapter 适配不同的 Agent 框架（OpenHarness、Claude Code、Codex 等）。

## 一、Agent宿主服务 - 使用 SDK 创建和管理 Agent 实例

    - 通过 agent-orchestrator 的 `OrchestratorClient` 创建和管理 Agent 实例
    - 支持唯一的 GUID 分配，创建实例时返回对应 GUID
    - 支持性能监控，防止超过限度的实例创建
    - 通过 Agent Adapter 支持操控不同框架的 Agent（执行命令、安装 Skill、配置 MCP 等）
    - 支持记忆同步：下载/上传远端记忆和配置
    - 每个 worker 进程独立持有 `OrchestratorClient`，通过 adapter 注入对应的 Agent 框架适配器

## 二、Agent 适配层 (`agents/`)

作为平台与 Agent 运行时之间的桥接层，实现 Agent Framework 的解耦。

    - 每个 Agent 框架对应一个独立适配器目录（如 `agents/openharness/`、`agents/claude-code/`）
    - 适配器实现 agent-orchestrator 的 `AgentAdapter` 协议（`build_exec_argv`、`build_exec_env`）
    - 适配器负责将通用的编排请求翻译为特定框架的 CLI 参数和环境变量
    - 宿主服务通过 adapter 参数注入适配器，无需修改 SDK 核心代码
    - 新增 Agent 框架只需添加一个适配器目录，无需改动平台代码

## 三、记忆服务 - 直接操作数据库按需存储数据

    - 存储用户各类型的定制化资产，使用路径的形式存储
    - 高扩展性、高性能的存储框架

## 四、Agent 市场服务 - 提供 Agent 定制服务与配置

    - 通过记忆服务或外部服务，获取已定制好的 Agent 模型和配置
    - 通过记忆服务或外部服务，获取 Skill 和 MCP
    - 支持 Agent 配置的发布与版本管理

## 五、用户与权限管理服务 - 支持企业级架构与权限管理

    - 支持企业级的组织定义
    - 为各级分配有组织标识的 API Key，每个 Key 可追溯上下级关系
    - 支持自定义的可扩展权限定义与管理
    - 使用记忆服务存储用户数据

## 六、中央调度与管理服务 - 集成相关服务的中央调度器

作为整个系统的中枢，负责服务编排、任务调度、计费聚合与全局状态管理。所有内部服务通过该服务协同工作。

### 6.1 服务注册与发现
- 维护各微服务（Agent 宿主、记忆、市场、权限）的注册表，支持服务健康检查与自动摘除
- 支持服务版本管理，兼容多版本并行运行与灰度切换
- 提供统一的服务状态查询接口，便于运维监控

### 6.2 Agent 申领流程编排
- 提供完整的 Agent 申领工作流：权限校验 → 配额检查 → 实例创建 → 资源分配 → 回调通知
- 支持申领审批机制：根据组织策略，某些 Agent 类型或高资源规格可配置为需审批
- 支持 Agent 实例的批量申领与预分配（企业级批量开通场景）
- 申领失败时自动回滚已分配资源，并返回明确错误码

### 6.3 计费与消耗统计引擎
- 通过 Agent宿主服务的性能监控数据，聚合各维度的 Token 消耗（input_tokens / output_tokens）
- 按组织层级（公司 → 部门 → 团队 → 个人）聚合费用统计，支持逐级汇总与穿透查询
- 支持多种计费模型：按量计费（per-token）、包月配额、预充值扣费
- 计费数据落盘到 PostgreSQL，支持历史账单导出与费用趋势分析
- 支持自定义计费规则：不同模型/不同 Agent 类型可配置差异化单价
- 提供费用告警机制：当组织或个人消耗接近阈值时自动触发通知

### 6.4 全局任务调度
- 封装 SDK 的 `InProcScheduler` 能力，提供异步任务队列
- 支持优先级调度：高优先级任务（如实例恢复）优先于常规任务（如批量查询）
- 支持定时任务：定时回收闲置 Agent 实例、定时生成费用报表、定时健康检查
- 任务状态追踪：pending → running → completed/failed，支持任务取消与重试
- 任务超时控制与死信队列，防止任务堆积

### 6.5 实例生命周期管理
- 统一管理 Agent 实例的完整生命周期，协调宿主服务与记忆服务
- 闲置检测：对长时间无交互的实例自动标记为 idle，触发资源回收策略
- 异常恢复：当宿主服务上报实例异常时，自动触发 SDK 的 `RecoverService` 进行恢复
- 实例状态全局视图：跨宿主节点的实例状态聚合查询

### 6.6 配置中心
- 全局配置统一管理：系统默认配置、组织级配置覆盖、实例级配置继承
- 配置热更新：修改配置后无需重启服务即可生效
- 配置版本管理：支持配置回滚与审计日志

### 6.7 事件总线
- 服务间异步通信基于事件驱动，降低耦合度
- 核心事件类型：`agent.created`、`agent.destroyed`、`agent.usage`、`quota.exceeded`、`approval.requested`、`approval.approved/rejected`
- 支持事件的持久化与回放，用于故障恢复与审计追溯
- 支持事件订阅过滤：各服务只订阅自己关心的事件

---

## 七、网关 - 接收请求并转发到对应的中央调度服务

作为系统的唯一入口，负责请求路由、认证鉴权、限流熔断与协议适配。对外暴露的完整 API 接口定义参见 [api-protocol.md](api-protocol.md)。

### 7.1 协议适配层
- 对外暴露 RESTful API（HTTP/HTTPS），企业内部前端/CLI 统一通过 HTTP 访问
- 预留 WebSocket 支持，用于 Agent 交互的实时流式响应（对应 SDK 的 `StreamEvent`）
- 预留 gRPC 通道，用于服务间高性能通信（网关到中央调度、中央调度到各微服务）
- API 版本管理：URL 前缀 `/api/v1/`，支持多版本共存
- 统一响应格式与错误码定义参见 [api-protocol.md 第 2 节](api-protocol.md#2-统一响应格式)

### 7.2 认证与鉴权中间件
- 所有请求必须携带有效的组织 API Key（由权限管理服务签发），网关层做基础校验
- 请求头格式：`Authorization: Bearer <org-apikey>` 或自定义 `X-OH-API-Key` 头
- 网关层校验 API Key 的有效性与组织归属，将解析后的身份信息（org_id、user_id、permissions）注入请求上下文
- 支持基于路径的鉴权预检：某些管理接口仅允许管理员角色访问
- API Key 过期与轮换机制：支持设置有效期，到期前自动提醒

### 7.3 请求路由
- 基于 URL path + method 的路由规则，将请求转发到中央调度服务的对应处理单元
- 完整路由表与接口定义参见 [api-protocol.md 第 3 节](api-protocol.md#3-路由表)

| 路径前缀 | 目标服务 | 说明 |
|---|---|---|
| `/api/v1/auth/*` | 权限管理服务（认证子模块） | 登录、Token 刷新、登出 |
| `/api/v1/agents/*` | 中央调度 → Agent 宿主服务 | 实例 CRUD、操控、记忆同步、流式交互 |
| `/api/v1/memory/*` | 中央调度 → 记忆服务 | 资产存储与检索 |
| `/api/v1/market/*` | 中央调度 → 市场服务 | 模板、Skill、MCP 浏览与订阅 |
| `/api/v1/builder/*` | 中央调度 → 市场服务 | Agent 定制构建（创建/编辑/发布 Agent 配置） |
| `/api/v1/org/*` | 中央调度 → 权限管理服务 | 组织、用户、API Key 管理 |
| `/api/v1/billing/*` | 中央调度 → 计费引擎 | 费用查询、账单导出、预算管理 |
| `/api/v1/tasks/*` | 中央调度 → Celery | 异步任务状态查询 |
| `/api/v1/approvals/*` | 中央调度 → 审批模块 | 审批列表与操作 |
| `/health` | 网关自身 | 健康检查 |

- 支持路由动态更新，新增服务无需重启网关

### 7.4 限流与熔断
- 多维度限流策略：
  - **全局限流**：网关层总 QPS 上限，防止系统过载
  - **组织级限流**：根据组织的套餐等级限制并发请求数
  - **用户级限流**：防止单一用户滥用
  - **接口级限流**：对高开销接口（如实例创建）设置独立限额
- 熔断机制：当下游服务连续失败达到阈值时，自动熔断并返回降级响应
- 限流算法：滑动窗口或令牌桶，可按需配置

### 7.5 请求日志与审计
- 全量记录请求日志：时间、来源 IP、API Key 标识、请求路径、响应状态码、耗时
- 审计日志独立存储，不可篡改，用于安全审计与问题排查
- 支持日志脱敏：请求体中的敏感字段（API Key、密码）自动掩码

### 7.6 负载均衡
- 当中央调度服务部署多实例时，网关负责请求的负载分发
- 支持轮询、加权轮询、最少连接数等策略
- 支持会话亲和性（sticky session）：同一用户的请求尽量路由到同一调度实例

### 7.7 错误处理与响应规范

- 统一错误响应格式与完整错误码表参见 [api-protocol.md 第 2 节](api-protocol.md#2-统一响应格式)
- 每个请求分配唯一 `request_id`，贯穿网关→调度→各服务，便于全链路追踪

### 7.8 部署与扩展
- 网关本身应为无状态服务，支持水平扩展
- 配置（路由表、限流规则、证书）通过中央配置中心下发，支持热重载
- 支持 TLS 终止，企业内网可选用 HTTP，跨网段强制 HTTPS

---

## 八、技术选型

### 8.1 整体原则
- 主语言统一为 Python 3.11+，与 agent-orchestrator SDK 保持技术栈一致，降低维护成本
- 框架选择追求简单可运维：开发阶段单机多进程即可运行，生产阶段可平滑过渡到真实分布式部署
- 依赖尽量少且成熟稳定，避免引入过重的框架
- SDK 作为 git submodule 引入，平台通过 adapter 层与具体 Agent 框架解耦

### 8.2 各层技术选型

| 层/服务 | 技术选型 | 选型理由 |
|---|---|---|
| 网关 | **FastAPI** + **Uvicorn** | 原生 async、自动 OpenAPI 文档、中间件生态成熟；Uvicorn 基于 uvloop 高性能 |
| Agent 宿主服务 | **FastAPI** + **多进程** + **agent-orchestrator** | 每个宿主 worker 独立进程内持有一个 `OrchestratorClient` 实例，通过 AgentAdapter 注入对应框架；进程隔离防止单个实例崩溃影响其他 |
| Agent 适配层 | **AgentAdapter Protocol** | SDK 定义的 `AgentAdapter` 协议，每个 Agent 框架一个适配器实现；当前内置 `openharness` 适配器 |
| 记忆服务 | **FastAPI** + **SQLAlchemy 2.0**（async） | SQLAlchemy 的 async engine + async session 支持高并发数据库操作 |
| Agent 市场服务 | **FastAPI** | 轻量 CRUD 服务，无重状态 |
| 权限管理服务 | **FastAPI** | 轻量 CRUD 服务 |
| 中央调度服务 | **FastAPI** + **Celery** | Celery 作为异步任务队列和定时任务调度器，任务定义在调度服务包中，worker 进程独立运行；与 Python 生态无缝集成 |
| 前端 | React + TypeScript + Ant Design + Zustand + Vite | 详见 [frontend-require.md](frontend-require.md) |
| 容器运行时 | **Podman**（无 daemon，rootless 可选）| 与 SDK 的 `PodmanDriver` 一致，无 daemon 架构更安全且无需 root 权限 |
| 进程管理 | **supervisor**（开发/单机）/ **Kubernetes**（生产） | 开发阶段 supervisor 管理各服务进程，生产阶段 K8s 管理调度 |

### 8.3 数据库选型

| 用途 | 选型 | 理由 |
|---|---|---|
| 结构化业务数据（实例记录、用户、组织、计费、权限） | **PostgreSQL 15+** | 企业级 RDBMS，支持 JSONB（灵活字段扩展）、行级锁、丰富索引类型；SQLAlchemy 原生支持 |
| 路径式资产存储（记忆服务） | **PostgreSQL** + **自定义路径索引** | 使用 `ltree` 扩展处理路径查询，或用 `TEXT` 列存储路径 + B-tree 索引；文件内容可存储在本地文件系统或对象存储中，数据库只存元数据 |
| 缓存与会话 | **Redis 7+** | 网关限流计数器、JWT Token 黑名单、服务注册心跳、Celery broker/backend |
| 事件总线 | **Redis Streams** | Celery 内置支持 Redis Streams 作为 broker；同时可用于服务间事件广播，无需额外引入 RabbitMQ/Kafka |
| 大文件/二进制资产 | **本地文件系统**（开发）/ **MinIO**（生产） | 记忆服务中的大文件存储在对象存储，数据库仅存元数据和路径引用 |

### 8.4 包管理与服务骨架

agent-orchestrator SDK 作为 git submodule 引入（`agent-orchestrator/`），平台代码通过 adapter 层与其交互。每个服务作为独立的 Python 包：

```
agent-platform/                          # 主仓库
├── .gitmodules                          # submodule 配置
├── agent-orchestrator/                  # SDK（git submodule: wlxms/agent-orchestrator）
│   ├── src/agent_orchestrator/
│   │   ├── contracts/adapter.py         # AgentAdapter Protocol 定义
│   │   ├── service/message_service.py   # 消息服务（支持 adapter 注入）
│   │   └── client.py                    # OrchestratorClient
│   └── pyproject.toml
├── agents/                              # Agent 框架适配器
│   └── openharness/                     # OpenHarness 适配器
│       ├── adapter.py                   # OpenHarnessAdapter 实现
│       └── config.py                    # 默认配置
├── services/
│   ├── gateway/                         # 网关
│   │   ├── pyproject.toml
│   │   └── src/agentp_gateway/
│   ├── host/                            # Agent 宿主服务
│   │   ├── pyproject.toml
│   │   └── src/agentp_host/
│   ├── memory/                          # 记忆服务
│   │   ├── pyproject.toml
│   │   └── src/agentp_memory/
│   ├── market/                          # Agent 市场服务
│   │   ├── pyproject.toml
│   │   └── src/agentp_market/
│   ├── auth/                            # 权限管理服务
│   │   ├── pyproject.toml
│   │   └── src/agentp_auth/
│   ├── billing/                         # 计费服务
│   │   ├── pyproject.toml
│   │   └── src/agentp_billing/
│   ├── scheduler/                       # 中央调度服务
│   │   ├── pyproject.toml
│   │   └── src/agentp_scheduler/
│   └── shared/                          # 公共库（模型、工具函数、配置基类）
│       ├── pyproject.toml
│       └── src/agentp_shared/
├── tests/                               # 集成测试
├── scripts/                             # 开发/部署脚本
│   ├── dev_start.ps1                    # 开发环境启动
│   └── verify_full_chain.ps1            # 全链路验证
├── frontend/                            # 前端 SPA
├── docs/                                # 文档
└── pyproject.toml                       # 顶层项目配置
```

`agentp_shared` 公共库提供：
- 统一的 Pydantic 模型（InstanceRecord、OrganizationRecord、UsageSnapshot 等，与 SDK contracts 对齐）
- 统一的错误体系（对应 SDK 的 `ErrorCode`/`OrchestratorError`）
- 请求上下文工具（RequestContext：tenant_id、user_id、org_id、permissions）
- 数据库连接工厂（create_async_engine 的统一封装）
- Redis 连接工厂
- 服务间调用的 HTTP 客户端封装

---

## 九、微服务实现与服务间交互

### 9.1 架构总览

系统采用**星型拓扑**：中央调度服务作为业务编排中枢，网关作为外部唯一入口。业务服务（Agent 宿主、市场、权限管理）处于同一层级，记忆服务下沉为基础设施层。

```
                         ┌──────────┐
                         │  前端 SPA │
                         └────┬─────┘
                              │ HTTP/WS
                         ┌────▼─────┐
                         │   网关    │
                         └────┬─────┘
                              │ HTTP (内网)
                    ┌─────────▼──────────┐
                    │   中央调度服务       │
                    │  (业务编排 + BFF)   │
                    └───┬────┬────┬─────┘
                        │    │    │
          ┌─────────────┤    │    ├─────────────┐
          │             │    │    │             │
    ┌─────▼─────┐  ┌───▼──▼┐ ┌─▼▼─────────┐
    │ Agent宿主  │  │市场   │ │权限管理     │
    │  服务(×N) │  │服务   │ │服务         │
    └─────┬─────┘  └───┬───┘ └─────┬───────┘
          │             │           │
          │    (业务服务通过 HTTP 调用记忆服务存取资产)
          │             │           │
          └──────┬──────┘           │
                 ▼                  ▼
          ┌─────────────────────────────────────────────────────┐
          │                    基础设施层                        │
          │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
          │  │ 记忆服务  │  │  Redis   │  │PostgreSQL│         │
          │  │(资产存储) │  │(缓存/事件)│  │(业务数据)│         │
          │  └──────────┘  └────┬─────┘  └──────────┘         │
          │                      │                               │
          │  ┌───────────────────▼──────────────────┐           │
          │  │  Celery (任务队列框架)                │           │
          │  │  Broker: Redis Streams               │           │
          │  │  Workers: 执行调度服务定义的异步/定时任务 │           │
          │  │  Beat: 定时触发器                     │           │
          │  └──────────────────────────────────────┘           │
          └─────────────────────────────────────────────────────┘
```

**层级职责说明**：
- **接入层**：网关（鉴权、限流、路由）
- **编排层**：中央调度服务（跨服务业务编排、请求聚合）
- **业务服务层**：Agent 宿主、市场服务、权限管理服务（各自独立进程，互不直接调用）
- **基础设施层**：
  - 记忆服务（路径式资产存取）
  - Redis（缓存/限流/事件总线/Celery Broker）
  - PostgreSQL（关系型业务数据）
  - Celery（异步任务执行框架，详见 9.1.1）

### 9.1.1 Celery 的定位与职责

**Celery 不是独立服务，而是基础设施层的任务执行框架**。它的代码和任务定义都归属于中央调度服务（`services/scheduler/`），worker 进程只是加载并执行这些任务代码的运行时。

```
services/scheduler/
├── src/scheduler/
│   ├── app.py          # FastAPI 应用（HTTP 接口 + 业务编排）
│   ├── tasks.py        # Celery 任务定义（异步任务 + 定时任务）
│   └── beat_schedule.py
├── pyproject.toml
```

**为什么用 Celery 而不是 FastAPI 原生的 async 或其他方案**：

| 对比维度 | FastAPI async | Python multiprocessing | Celery |
|---|---|---|---|
| 任务持久化 | 进程重启即丢失 | 进程重启即丢失 | 任务存储在 Redis Broker，进程重启后可恢复 |
| 重试机制 | 需手动实现 | 需手动实现 | 内置 `max_retries`、`retry_backoff`、自动死信 |
| 定时调度 | 需额外引入 APScheduler | 不支持 | 内置 Celery Beat，配置声明式 |
| 任务状态追踪 | 需手动实现 | 需手动实现 | 内置 `task_id`、状态机（PENDING→STARTED→SUCCESS/FAILURE） |
| 多 worker 分布 | 单进程内协程 | 单机多进程 | 跨机器分布式 worker |
| 与 Redis 集成 | 需手动管理 | 不支持 | 原生支持 Redis 作为 Broker + Backend |

在本系统中的具体使用场景：

1. **异步任务**：创建 Agent 实例（涉及调用宿主服务 + 初始化记忆，耗时较长，需要重试）
2. **定时任务**：
   - 每小时扫描并回收闲置 Agent 实例
   - 每天凌晨生成费用报表
   - 定时健康检查各服务状态
3. **延迟任务**：审批超时自动驳回、实例到期提醒
4. **重试保障**：宿主服务临时不可用时，任务自动等待后重试，无需人工干预

**关键约束**：Celery 的任务函数必须是**可序列化的纯逻辑**，不能持有数据库连接或 HTTP 客户端等状态。任务执行时通过 `agentp_shared` 的工厂函数按需创建连接。

### 9.1.2 关于"其他服务通过记忆服务操作数据库"的设计决策

**不建议所有服务都通过记忆服务间接操作数据库**。原因如下：

1. **职责不同**：记忆服务负责**路径式资产存储**（Skill 包、MCP 配置、用户记忆文件、模板文件等非结构化/半结构化数据），本质是一个 KV + 文件存储抽象；而权限服务需要管理组织树、角色关联、API Key 等关系型数据，计费引擎需要聚合查询、时间序列统计，这些是典型的结构化 CRUD + 聚合分析场景
2. **性能瓶颈**：所有数据库操作都经过一个服务会形成单点瓶颈，且增加一跳网络延迟
3. **事务完整性**：权限服务和计费引擎各自有复杂的事务需求（如创建 API Key 的原子操作），通过 HTTP 调用记忆服务无法保证数据库事务

**正确的数据访问策略**：

| 数据类型 | 访问方式 | 示例 |
|---|---|---|
| 路径式资产（文件、模板、Skill 包、记忆文件） | **通过记忆服务 HTTP API** | 上传 Skill 包到 `org-001/skills/dev-001/analyzer.zip` |
| 关系型业务数据（用户、组织、API Key、权限） | **各服务直接连接 PostgreSQL** | 权限服务直接查询 `organizations` 表 |
| 计费流水、实例记录 | **各服务直接连接 PostgreSQL** | 计费引擎直接 `INSERT INTO usage_records` |
| 缓存、限流、事件 | **各服务直接连接 Redis** | 网关直接操作 Redis 计数器 |

记忆服务的定位是**统一的数据资产存取层**，而非通用的数据库代理。业务服务直接使用 `agentp_shared` 提供的数据库连接工厂访问 PostgreSQL，记忆服务专注于路径式资产场景。

### 9.2 服务间通信方式

系统采用三种通信方式，按场景选择：

#### 方式一：同步 HTTP 调用（请求-响应模式）

**适用场景**：需要即时返回结果的操作（查询实例状态、创建实例、权限校验等）

**实现**：服务内部通过 `httpx.AsyncClient` 调用目标服务的内网 HTTP 端口。

```python
# agentp_shared 中提供的服务调用工具
class ServiceClient:
    """封装服务间同步调用，自动注入 request_id 和租户信息"""

    def __init__(self, service_registry: dict[str, str]):
        # service_registry = {"host": "http://host:8001", "memory": "http://memory:8002", ...}
        self._client = httpx.AsyncClient(timeout=30.0)
        self._registry = service_registry

    async def call(
        self,
        service: str,
        method: str,
        path: str,
        *,
        ctx: RequestContext,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        url = f"{self._registry[service]}{path}"
        headers = {
            "X-Request-ID": ctx.request_id,
            "X-Tenant-ID": ctx.tenant_id,
            "X-User-ID": ctx.user_id,
            "X-Internal-Call": "true",  # 标记内部调用，跳过网关鉴权
        }
        resp = await self._client.request(method, url, json=json, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()
```

**调用链路**：

```
前端 → 网关(鉴权/限流) → 中央调度(路由) → 目标服务(业务逻辑) → 数据库
                                    ↓
                              （如需调用其他服务）
                                    ↓
                              中央调度 → 其他服务
```

中央调度服务作为**BFF（Backend for Frontend）**层，所有跨服务编排逻辑集中于此。各微服务只暴露原子接口，不做跨服务调用。示例：

- 创建 Agent 请求：`网关 → 调度 → 权限服务(校验配额) → 宿主服务(创建实例) → 记忆服务(初始化记忆) → 返回结果`
- 查询费用：`网关 → 调度 → 计费引擎(聚合数据) → 返回结果`

#### 方式二：异步事件广播（发布-订阅模式）

**适用场景**：不需要即时返回、解耦上下游的操作（实例状态变更通知、用量上报、审批通知等）

**实现**：基于 Redis Streams 的轻量级事件总线。

```python
# agentp_shared/event_bus.py
import json
import asyncio
from dataclasses import dataclass
from redis.asyncio import Redis

@dataclass
class Event:
    topic: str          # e.g. "agent.created"
    payload: dict
    source: str         # 发布者服务名
    request_id: str     # 链路追踪ID

class EventBus:
    def __init__(self, redis: Redis):
        self._redis = redis
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, topic: str, handler: Callable):
        self._handlers.setdefault(topic, []).append(handler)

    async def publish(self, event: Event):
        await self._redis.xadd(
            f"agentp:events:{event.topic}",
            {
                "payload": json.dumps(event.payload),
                "source": event.source,
                "request_id": event.request_id,
            },
            maxlen=10000,  # 流最大长度，防止内存泄漏
        )

    async def consume(self, service_name: str):
        """各服务启动一个消费者协程，持续消费自己关心的事件"""
        for topic, handlers in self._handlers.items():
            group = f"{service_name}:{topic}"
            try:
                await self._redis.xgroup_create(f"agentp:events:{topic}", group, id="0", mkstream=True)
            except Exception:
                pass  # group 已存在
            asyncio.create_task(self._poll(topic, group, handlers))
```

**事件流向**：

```
宿主服务 ──publish──→ Redis Streams("agent.created") ──consume──→ 计费引擎（初始化费用记录）
                                                      ──consume──→ 事件日志（持久化审计）
                                                      ──consume──→ 通知服务（可选）
```

各服务在启动时注册自己关心的事件处理器，通过 Redis Streams consumer group 实现可靠的至少一次消费。

#### 方式三：Celery 异步任务（延迟/定时任务）

**适用场景**：耗时操作、定时任务、需要重试机制的操作（批量实例创建、闲置回收、报表生成、异常恢复）

**实现**：中央调度服务集成的 Celery worker。

```python
# scheduler/tasks.py
from celery import Celery

app = Celery("agentp_scheduler", broker="redis://localhost:6379/0", backend="redis://localhost:6379/1")

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def create_instance_async(self, instance_config: dict, ctx: dict):
    """异步创建实例（含重试）"""
    try:
        # 调用宿主服务的内部接口
        result = sync_call_service("host", "POST", "/internal/instances", json=instance_config, ctx=ctx)
        return result
    except Exception as exc:
        raise self.retry(exc=exc)

@app.task
def recycle_idle_instances():
    """定时任务：回收闲置实例"""
    instances = sync_call_service("host", "GET", "/internal/instances", params={"status": "idle"})
    for inst in instances:
        sync_call_service("host", "DELETE", f"/internal/instances/{inst['instance_id']}")

@app.task
def generate_daily_billing_report(org_id: str):
    """定时任务：生成日报表"""
    ...

# Celery Beat 定时配置
app.conf.beat_schedule = {
    "recycle-idle-every-hour": {
        "task": "scheduler.tasks.recycle_idle_instances",
        "schedule": 3600.0,  # 每小时
    },
    "daily-billing-report": {
        "task": "scheduler.tasks.generate_daily_billing_report",
        "schedule": crontab(hour=2, minute=0),  # 每天凌晨2点
    },
}
```

### 9.3 各服务内部实现要点

#### 9.3.1 网关实现

```python
# gateway/app.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

app = FastAPI(title="agent-platform Gateway")

# 中间件链：CORS → 限流 → 鉴权 → 路由转发
@app.middleware("http")
async def gateway_pipeline(request: Request, call_next):
    # 1. 健康检查跳过
    if request.url.path == "/health":
        return await call_next(request)

    # 2. 鉴权中间件：校验 API Key / JWT
    auth_result = await authenticate(request)
    if not auth_result.ok:
        return JSONResponse(status_code=401, content={"code": "UNAUTHORIZED", "message": auth_result.reason})

    # 3. 限流中间件：检查是否超限
    if not await check_rate_limit(auth_result.org_id, auth_result.user_id):
        return JSONResponse(status_code=429, content={"code": "RATE_LIMITED", "message": "Too many requests"})

    # 4. 注入身份信息到请求头，转发到中央调度
    # 5. 路由转发
    ...
```

网关本质是一个反向代理，核心逻辑是：鉴权 → 限流 → 转发。不包含业务逻辑，保持无状态。

#### 9.3.2 Agent 宿主服务实现

宿主服务是整个系统最关键的服务，通过 agent-orchestrator SDK 操控 Agent 实例。其内部采用**进程池模型 + Adapter 注入**：

```
宿主服务主进程（FastAPI HTTP Server）
    │
    ├── 进程池（N 个 worker 进程）
    │   ├── Worker-0: OrchestratorClient(adapter=OpenHarnessAdapter())
    │   ├── Worker-1: OrchestratorClient(adapter=OpenHarnessAdapter())
    │   └── Worker-N: OrchestratorClient(adapter=OpenHarnessAdapter())
    │
    └── 状态追踪（主进程内存 + PostgreSQL 持久化）
```

```python
# host/app.py
from fastapi import FastAPI
from agent_orchestrator import OrchestratorClient
from agents.openharness.adapter import OpenHarnessAdapter
from agents.openharness.config import DEFAULT_CONFIG

app = FastAPI(title="Agent Host Service")

# 适配器：桥接 orchestrator 与具体 Agent 框架
adapter = OpenHarnessAdapter(DEFAULT_CONFIG)

# 进程池：每个 worker 独立持有 SDK 客户端
class HostWorker:
    """运行在独立进程中，持有 OrchestratorClient"""
    def __init__(self):
        self.client = OrchestratorClient(
            adapter=adapter,
            allowed_roots=config.ALLOWED_ROOTS,
            runtime="podman",
            podman_image=config.PODMAN_IMAGE,
            db_path=":memory:",  # 宿主服务用 PostgreSQL，worker 内部用内存
        )

    def create_instance(self, req_dict: dict) -> dict:
        req = InstanceCreateRequest(**req_dict)
        record = self.client.create_instance(req)
        return record.model_dump()

    def send_message(self, instance_id: str, prompt: str, **kwargs) -> dict:
        result = self.client.send_message(instance_id, prompt, **kwargs)
        return result.model_dump()

# 使用 multiprocessing 替代 ProcessPoolExecutor（因为需要 fork 出带状态的 worker）
def _worker_loop(task_queue: multiprocessing.Queue, result_queue: multiprocessing.Queue):
    """worker 进程主循环：从队列取任务，执行，返回结果"""
    worker = HostWorker()
    while True:
        task = task_queue.get()
        if task is None:  # 毒丸信号，退出
            break
        try:
            method = getattr(worker, task["method"])
            result = method(*task["args"], **task["kwargs"])
            result_queue.put({"task_id": task["task_id"], "status": "ok", "data": result})
        except Exception as e:
            result_queue.put({"task_id": task["task_id"], "status": "error", "error": str(e)})
```

**宿主服务与 SDK 的集成要点**：
- 每个 worker 进程独立持有 `OrchestratorClient`，通过 `adapter` 参数注入 Agent 框架适配器
- 适配器（如 `OpenHarnessAdapter`）负责将编排请求翻译为具体框架的 CLI 参数和环境变量
- 新增 Agent 框架只需实现 `AgentAdapter` 协议并注入宿主服务，无需修改 SDK 或平台核心代码
- `PodmanDriver` 通过 Podman CLI（`subprocess`）与宿主机 Podman 通信
- `SQLiteStore` 在 worker 内使用 `:memory:` 模式仅做请求去重，持久化数据同步写入 PostgreSQL（由主进程负责）
- worker 通过 multiprocessing.Queue 与主进程通信，主进程（FastAPI）将 HTTP 请求序列化为 task dict 投递到对应 worker 的队列

#### 9.3.3 记忆服务实现

```python
# memory/app.py
from fastapi import FastAPI, UploadFile, File
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

app = FastAPI(title="Memory Service")

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/agentp")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)

# 路径式存储 API
@app.get("/api/v1/memory/{org_id}/**:path")
async def get_asset(org_id: str, path: str):
    """按路径获取资产，支持递归列出目录内容"""
    ...

@app.put("/api/v1/memory/{org_id}/**:path")
async def put_asset(org_id: str, path: str, content: UploadFile = File(...)):
    """上传资产到指定路径"""
    ...

@app.delete("/api/v1/memory/{org_id}/**:path")
async def delete_asset(org_id: str, path: str):
    """删除指定路径资产"""
    ...
```

记忆服务的核心是路径式 KV 存储，路径格式为 `{org_id}/{category}/{user_id}/{asset_name}`，例如：
- `org-001/skills/dev-team-001/python-analyzer.zip`
- `org-001/memories/user-042/session-config.json`
- `org-001/templates/general-assistant/agent.yaml`

#### 9.3.4 中央调度服务实现

中央调度服务是业务编排层，封装所有跨服务调用：

```python
# scheduler/app.py
from fastapi import FastAPI, Depends
from agentp_shared import ServiceClient, RequestContext, EventBus

app = FastAPI(title="Central Scheduler")
svc = ServiceClient(service_registry=config.SERVICE_REGISTRY)
bus = EventBus(redis=get_redis())

@app.post("/api/v1/agents")
async def create_agent(req: AgentCreateRequest, ctx: RequestContext = Depends(get_context)):
    """编排：权限校验 → 配额检查 → 创建实例 → 初始化记忆 → 发布事件"""
    # 1. 权限校验
    perm = await svc.call("auth", "GET", f"/internal/orgs/{ctx.org_id}/quota", ctx=ctx)
    if perm["current"] >= perm["quota"]:
        raise HTTPException(403, detail={"code": "QUOTA_EXCEEDED", ...})

    # 2. 创建实例（同步调用宿主服务）
    instance = await svc.call("host", "POST", "/internal/instances", json=req.model_dump(), ctx=ctx)

    # 3. 初始化记忆空间
    await svc.call("memory", "PUT", f"/internal/assets/{ctx.org_id}/instances/{instance['instance_id']}/.init", ctx=ctx)

    # 4. 发布事件（异步，不阻塞返回）
    await bus.publish(Event(topic="agent.created", payload=instance, source="scheduler", request_id=ctx.request_id))

    return instance

@app.post("/api/v1/agents/{id}/message")
async def send_message(id: str, req: MessageRequest, ctx: RequestContext = Depends(get_context)):
    """转发消息到宿主服务"""
    return await svc.call("host", "POST", f"/internal/instances/{id}/message", json=req.model_dump(), ctx=ctx)
```

### 9.4 服务启动与进程模型

#### 开发/单机模式（supervisor 管理）

使用 `scripts/dev_start.ps1` 管理所有进程（开发阶段），单机运行全部服务：

当前开发阶段端口分配：

| 服务 | 端口 | 包名 |
|---|---|---|
| 网关 | 8000 | `agentp_gateway` |
| 认证/权限 | 8001 | `agentp_auth` |
| Agent 宿主 | 8002 | `agentp_host` |
| 中央调度 | 8003 | `agentp_scheduler` |
| 记忆服务 | 8004 | `agentp_memory` |
| 市场服务 | 8005 | `agentp_market` |
| 计费服务 | 8006 | `agentp_billing` |

此模式下：
- 网关对外暴露 `:8000`，所有外部请求走网关
- 各微服务绑定 `127.0.0.1` 仅内网可访问
- PostgreSQL（:5432）和 Redis（:6379）通过 Podman 容器运行
- 宿主服务的 worker 进程池数量默认 = CPU 核数

#### 生产模式（K8s 部署）

```
Namespace: agent-platform
├── Deployment: gateway          (replicas: 2+, 无状态)
├── Deployment: scheduler        (replicas: 2+, 无状态)
├── Deployment: host             (replicas: N, 有状态-绑定宿主节点)
│   └── PodAnnotations: node-name
├── Deployment: memory           (replicas: 2+, 无状态)
├── Deployment: market           (replicas: 1+, 无状态)
├── Deployment: auth             (replicas: 2+, 无状态)
├── Deployment: celery-worker    (replicas: 4+, 无状态)
├── Deployment: celery-beat      (replicas: 1, leader-election)
├── StatefulSet: postgres        (replicas: 1, PVC)
├── StatefulSet: redis           (replicas: 1, 或使用 Redis Cluster)
├── Service: gateway-svc         (ClusterIP / LoadBalancer)
├── Service: internal-svc        (ClusterIP, 各服务间调用)
└── Ingress: gateway-ingress     (TLS 终止)
```

关键变化：
- 宿主服务的 Deployment 需要使用 `nodeAffinity` 绑定到安装了 Podman 的节点
- Redis 可替换为 Redis Cluster 以提升可用性
- PostgreSQL 可使用云托管 RDS 或 Patroni 高可用方案
- `ServiceClient` 中的 `service_registry` 在 K8s 中使用 Service 名称（如 `http://memory-service:8002`）

### 9.5 服务注册与服务发现

不引入独立的注册中心（如 Consul/Etcd），采用**静态配置 + 健康检查**的轻量方案：

```python
# agentp_shared/config.py 中通过 pydantic-settings 管理配置
# 环境变量前缀统一为 AGENTP_（pydantic-settings 自动全大写匹配）
GATEWAY_PORT = 8000; AUTH_PORT = 8001; HOST_PORT = 8002
SCHEDULER_PORT = 8003; MEMORY_PORT = 8004; MARKET_PORT = 8005; BILLING_PORT = 8006

class DatabaseSettings(BaseSettings):
    url: str = "postgresql+asyncpg://agentp:agentp_dev@localhost:5432/agent_platform"
    model_config = {"env_prefix": "AGENTP_DB_"}

class RedisSettings(BaseSettings):
    url: str = "redis://localhost:6379/0"
    model_config = {"env_prefix": "AGENTP_REDIS_"}

class JWTSettings(BaseSettings):
    secret_key: str = "agentp-dev-secret-key-change-in-production"
    model_config = {"env_prefix": "AGENTP_JWT_"}

# 每个服务暴露 /health 端点，中央调度服务定期探测
@app.get("/health")
async def health():
    return {"status": "ok", "service": "host", "version": "0.1.0"}
```

K8s 模式下由 Kubernetes Service 自动提供服务发现；单机模式下通过 supervisor 的进程管理隐含了服务可用性（进程挂了 supervisor 自动重启）。

### 9.6 数据一致性策略

系统采用**最终一致性**模型，不做分布式事务：

| 场景 | 一致性策略 |
|---|---|
| 创建 Agent（跨宿主+记忆+计费） | 宿主服务创建成功后发布 `agent.created` 事件，记忆服务和计费引擎各自消费事件做初始化；若消费失败，Celery worker 重试 |
| Agent 用量上报 | 宿主服务在每次消息交互后发布 `agent.usage` 事件，计费引擎异步累加 |
| 权限变更 | 权限服务更新后发布 `permission.changed` 事件，网关清除对应缓存 |
| 闲置回收 | 定时任务扫描超时实例，发布 `agent.recycle` 事件，宿主服务消费并执行销毁 |

关键原则：**核心链路同步（创建实例必须成功才能返回），辅助链路异步（计费、通知可延迟）**。