import apiClient from './client';
import type {
  AgentInstance, CreateAgentRequest, BatchIdsRequest,
  CommandRequest, CommandResponse, MonitorStats, MemoryTreeNode,
  SkillInstallRequest, McpConfig, AgentModelConfig,
  PaginatedResponse, DataResponse,
} from '@/types';

export const agentsApi = {
  list: (params?: { page?: number; page_size?: number; status?: string; name?: string; created_after?: string; org_id?: string }) =>
    apiClient.get<any, PaginatedResponse<AgentInstance>>('/api/v1/agents', { params }),

  get: (id: string) =>
    apiClient.get<any, DataResponse<AgentInstance>>(`/api/v1/agents/${id}`),

  create: (data: CreateAgentRequest) =>
    apiClient.post<any, DataResponse<{ id: string; task_id: string }>>('/api/v1/agents', data),

  destroy: (id: string) =>
    apiClient.delete<any, DataResponse<{ ok: boolean }>>(`/api/v1/agents/${id}`),

  restart: (id: string) =>
    apiClient.post<any, DataResponse<{ ok: boolean }>>(`/api/v1/agents/${id}/restart`),

  stop: (id: string) =>
    apiClient.post<any, DataResponse<{ ok: boolean }>>(`/api/v1/agents/${id}/stop`),

  batchRestart: (data: BatchIdsRequest) =>
    apiClient.post<any, DataResponse<Array<{ id: string; ok: boolean }>>>('/api/v1/agents/batch-restart', data),

  batchDestroy: (data: BatchIdsRequest) =>
    apiClient.post<any, DataResponse<{ ok: boolean }>>('/api/v1/agents/batch-destroy', data),

  sendMessage: (id: string, data: { message: string; stream?: boolean }) =>
    apiClient.post<any, DataResponse<{ reply: string }>>(`/api/v1/agents/${id}/message`, data),

  executeCommand: (id: string, data: CommandRequest) =>
    apiClient.post<any, DataResponse<CommandResponse>>(`/api/v1/agents/${id}/command`, data),

  installSkill: (id: string, data: SkillInstallRequest) =>
    apiClient.post<any, DataResponse<{ ok: boolean }>>(`/api/v1/agents/${id}/skills`, data),

  addMcp: (id: string, data: McpConfig) =>
    apiClient.post<any, DataResponse<{ ok: boolean; name: string }>>(`/api/v1/agents/${id}/mcp`, data),

  updateConfig: (id: string, data: Partial<AgentModelConfig & { system_prompt?: string; permission_mode?: string }>) =>
    apiClient.put<any, DataResponse<{ updated_fields: string[] }>>(`/api/v1/agents/${id}/config`, data),

  getMonitor: (id: string) =>
    apiClient.get<any, DataResponse<MonitorStats>>(`/api/v1/agents/${id}/monitor`),

  getMemoryTree: (id: string, params?: { path?: string }) =>
    apiClient.get<any, DataResponse<{ paths: string[]; tree: MemoryTreeNode[] }>>(`/api/v1/agents/${id}/memory/tree`, { params }),

  uploadMemory: (id: string, formData: FormData) =>
    apiClient.post<any, DataResponse<{ ok: boolean }>>(`/api/v1/agents/${id}/memory/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  downloadMemory: (id: string, path: string) =>
    apiClient.get<any, Blob>(`/api/v1/agents/${id}/memory/download`, { params: { path }, responseType: 'blob' }),
};
