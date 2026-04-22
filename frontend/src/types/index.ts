// ─── Core Response Types ───────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface DataResponse<T> {
  data: T;
}

export interface OkResponse {
  ok: true;
  task_id?: string;
}

export interface ErrorResponse {
  code: ErrorCode;
  message: string;
  request_id?: string;
  details?: {
    fields?: Record<string, string[]>;
    required_role?: string;
    resource?: string;
    id?: string;
    field?: string;
    quota?: number;
    current?: number;
    retry_after?: number;
    migration?: string;
    service?: string;
    [key: string]: unknown;
  };
}

export type ErrorCode =
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'QUOTA_EXCEEDED'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'API_DEPRECATED'
  | 'VALIDATION_ERROR'
  | 'RATE_LIMITED'
  | 'INTERNAL_ERROR'
  | 'UPSTREAM_UNAVAILABLE'
  | 'SERVICE_UNAVAILABLE';

// ─── User & Auth ──────────────────────────────────────────────────

export type UserRole = 'super_admin' | 'org_admin' | 'team_admin' | 'user';

export interface User {
  id: string;
  username: string;
  role: UserRole;
  org_id: string;
  permissions?: string[];
  created_at?: string;
}

export interface LoginRequest {
  api_key: string;
}

export interface LoginResponse {
  token: string;
  refresh_token: string;
  expires_at?: string;
  user: User;
}

export interface RefreshResponse {
  token: string;
  refresh_token: string;
  expires_at?: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

// ─── Agent Instance ───────────────────────────────────────────────

export type AgentStatus =
  | 'creating'
  | 'running'
  | 'seeding'
  | 'ready'
  | 'stopping'
  | 'stopped'
  | 'failed';

export interface AgentModelConfig {
  provider: string;
  model: string;
  api_base?: string;
  api_key?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
}

export type PermissionMode = 'default' | 'plan' | 'acceptEdits' | 'bypassPermissions';

export interface AgentInstance {
  id: string;
  name: string;
  guid: string;
  status: AgentStatus;
  host_node?: string;
  model_config?: AgentModelConfig;
  model?: string;
  config?: Record<string, unknown>;
  system_prompt?: string;
  permission_mode?: PermissionMode;
  resource_spec?: 'lightweight' | 'standard' | 'high_performance';
  owner_id?: string;
  org_id?: string;
  config_id?: string;
  task_id?: string;
  created_at: string;
  updated_at?: string;
  last_active_at?: string;
}

export interface AgentListItem {
  id: string;
  guid: string;
  name: string;
  status: AgentStatus;
  host_node?: string;
  model?: string;
  created_at: string;
  last_active_at?: string;
}

export interface CreateAgentRequest {
  name: string;
  template_id?: string;
  agent_config_id?: string;
  model?: AgentModelConfig;
  config?: Record<string, unknown>;
  resource_spec?: 'lightweight' | 'standard' | 'high_performance';
}

export interface BatchIdsRequest {
  ids: string[];
}

export interface CommandRequest {
  command: string;
  timeout?: number;
}

export interface CommandResponse {
  output: string;
  exit_code?: number;
}

export interface MessageRequest {
  prompt: string;
  stream?: boolean;
}

export interface MonitorStats {
  cpu_percent: number;
  memory_mb: number;
  memory_percent?: number;
  total_tokens: number;
  input_tokens?: number;
  output_tokens?: number;
}

export interface MemoryTreeResponse {
  paths: string[];
  tree: MemoryTreeNode;
}

export interface MemoryTreeNode {
  path: string;
  name?: string;
  type: 'file' | 'directory';
  size?: number;
  modified_at?: string;
  children?: MemoryTreeNode[];
}

export interface SkillInstallRequest {
  skill_id: string;
}

export interface McpConfigRequest {
  name: string;
  transport: 'stdio' | 'http' | 'ws';
  config: Record<string, unknown>;
}

export interface AgentConfigUpdateRequest {
  system_prompt?: string;
  permission_mode?: PermissionMode;
  model?: AgentModelConfig;
}

// ─── Agent Builder / Config ───────────────────────────────────────

export type Visibility = 'private' | 'org' | 'public';
export type ToneStyle = 'professional' | 'friendly' | 'concise' | 'creative';
export type DefaultLanguage = 'zh-CN' | 'en-US' | 'auto';
export type TemplateCategory =
  | 'code_development'
  | 'data_analysis'
  | 'ops_automation'
  | 'general_assistant';

export interface McpConfig {
  name: string;
  transport: 'stdio' | 'http' | 'ws';
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
  url?: string;
  headers?: Record<string, string>;
}

export interface WorkspacePreloadItem {
  source: 'memory' | 'embedded' | 'url';
  path?: string;
  filename?: string;
  content?: string;
  url?: string;
}

export interface AgentConfig {
  id: string;
  name: string;
  description: string;
  version: string;
  author_id: string;
  org_id: string;
  visibility: Visibility;
  personality: {
    system_prompt: string;
    critical_reminder?: string;
    initial_prompt?: string;
    tone: ToneStyle;
    language: DefaultLanguage;
  };
  model: {
    provider: string;
    litellm_params: {
      model: string;
      api_base?: string;
      api_key?: string;
      temperature?: number;
      max_tokens?: number;
      top_p?: number;
      frequency_penalty?: number;
      presence_penalty?: number;
      num_ctx?: number;
      drop_params?: boolean;
      custom_llm_provider?: string;
      timeout?: number;
      max_retries?: number;
      extra_headers?: Record<string, string>;
    };
  };
  tools: {
    allowed: string[];
    disallowed: string[];
  };
  skills: string[];
  mcp_servers: McpConfig[];
  workspace: {
    enabled: boolean;
    preload_paths: WorkspacePreloadItem[];
  };
  permissions: {
    mode: PermissionMode;
    max_turns: number;
  };
  appearance: {
    color?: string;
    icon?: string;
  };
  created_at: string;
  updated_at: string;
}

export interface CreateAgentConfigRequest {
  name: string;
  description: string;
  visibility?: Visibility;
  personality?: Partial<AgentConfig['personality']>;
  model?: Partial<AgentConfig['model']>;
  tools?: Partial<AgentConfig['tools']>;
  skills?: string[];
  mcp_servers?: McpConfig[];
  workspace?: Partial<AgentConfig['workspace']>;
  permissions?: Partial<AgentConfig['permissions']>;
  appearance?: Partial<AgentConfig['appearance']>;
}

export interface UpdateAgentConfigRequest extends Partial<CreateAgentConfigRequest> {}

export interface ConfigValidationResult {
  valid: boolean;
  warnings: string[];
  errors: string[];
}

export interface PublishConfigRequest {
  visibility: 'org' | 'public';
  category?: string;
  tags?: string[];
}

export interface DuplicateConfigRequest {
  name: string;
}

export interface ConfigVersion {
  version: string;
  changelog?: string;
  created_at: string;
}

export interface ConfigPreviewResponse {
  preview_id: string;
  expires_at: string;
}

export interface ImportConfigRequest {
  source: 'file' | 'url';
  content: string;
}

// ─── Market ───────────────────────────────────────────────────────

export interface Template {
  id: string;
  name: string;
  description: string;
  category?: string;
  category_name?: string;
  scenario: string;
  skills: Array<{ id: string; name: string }>;
  mcp_servers: Array<{ id: string; name: string; transport?: string }>;
  resource_spec: {
    cpu?: string;
    memory?: string;
    gpu?: string;
  };
  usage_count: number;
  author?: string;
  version?: string;
  created_at: string;
  updated_at: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string;
  author: string;
  version: string;
  package_url?: string;
  category?: string;
}

export interface McpServerItem {
  id: string;
  name: string;
  description: string;
  transport: 'stdio' | 'http' | 'ws';
  config_template: Record<string, unknown>;
}

export interface MarketCategory {
  id: string;
  name: string;
  icon?: string;
  sort_order?: number;
}

// ─── Billing ──────────────────────────────────────────────────────

export interface BillingSummary {
  total_tokens: number;
  total_cost: number;
  budget?: number;
  budget_remaining?: number;
  by_instance?: Array<{
    agent_id: string;
    agent_name: string;
    tokens: number;
    cost: number;
  }>;
  by_model?: Array<{
    model: string;
    tokens: number;
    cost: number;
  }>;
  daily_trend?: Array<{
    date: string;
    tokens: number;
    cost: number;
  }>;
}

export interface BillingRecord {
  id: string;
  time: string;
  agent_id: string;
  agent_name?: string;
  instance_name?: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
  currency?: string;
}

export interface BudgetInfo {
  threshold: number;
  alert_rules?: Array<Record<string, unknown>>;
}

export interface SetBudgetRequest {
  threshold: number;
  alert_rules?: Array<Record<string, unknown>>;
}

// ─── Organization ─────────────────────────────────────────────────

export interface OrgNode {
  id: string;
  name: string;
  parent_id?: string;
  depth?: number;
  quota?: number;
  member_count?: number;
  agent_count?: number;
  description?: string;
  children?: OrgNode[];
}

export interface OrgDetail extends OrgNode {
  depth: number;
  quota: number;
  member_count: number;
}

export interface CreateOrgRequest {
  name: string;
  parent_id?: string;
  quota?: number;
}

export interface OrgMember {
  id: string;
  user_id: string;
  username: string;
  role: UserRole;
  org_id: string;
  joined_at?: string;
}

export interface AddMemberRequest {
  user_id: string;
  role: UserRole;
}

export interface UpdateMemberRoleRequest {
  role: UserRole;
}

// ─── API Keys ─────────────────────────────────────────────────────

export interface ApiKey {
  id: string;
  label: string;
  user_id: string;
  permissions?: string[];
  org_id?: string;
  created_at: string;
  expires_at?: string;
  last_used_at?: string;
}

export interface CreateApiKeyRequest {
  label: string;
  permissions?: string[];
  expires_in_days?: number;
}

export interface CreateApiKeyResponse {
  id: string;
  api_key: string;
  expires_at?: string;
}

export interface RenewApiKeyRequest {
  expires_in_days: number;
}

export interface RenewApiKeyResponse {
  expires_at: string;
}

// ─── Permissions & Roles ─────────────────────────────────────────

export interface Permission {
  id: string;
  name: string;
  description: string;
}

export interface Role {
  id: string;
  name: string;
  permissions: string[];
}

export interface UpdateRoleRequest {
  permissions: string[];
}

// ─── Approvals ────────────────────────────────────────────────────

export type ApprovalStatus = 'pending' | 'approved' | 'rejected';

export interface Approval {
  id: string;
  applicant: string;
  applicant_name: string;
  org_id?: string;
  created_at: string;
  template_name?: string;
  config_summary?: Record<string, unknown>;
  reason?: string;
  status: ApprovalStatus;
  review_comment?: string;
  reviewer_id?: string;
  reviewed_at?: string;
}

export interface RejectApprovalRequest {
  reason: string;
}

// ─── Memory ───────────────────────────────────────────────────────

export interface MemoryAsset {
  path: string;
  name: string;
  type: 'file' | 'dir';
  size?: number;
  updated_at?: string;
  content?: string;
  content_type?: string;
  created_at?: string;
}

// ─── Async Tasks ──────────────────────────────────────────────────

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface TaskInfo {
  id: string;
  status: TaskStatus;
  result?: Record<string, unknown>;
  error?: string;
}

// ─── Health ───────────────────────────────────────────────────────

export interface ServiceHealth {
  service: string;
  status: 'ok' | 'unavailable' | 'error';
  latency_ms?: number;
  details?: string;
}

export interface AggregateHealth {
  services: ServiceHealth[];
  overall: 'ok' | 'degraded' | 'down';
}
