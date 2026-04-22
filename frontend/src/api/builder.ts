import apiClient from './client';
import type {
  AgentConfig, CreateAgentConfigRequest, ConfigValidationResult,
  Visibility, PaginatedResponse, DataResponse,
} from '@/types';

export const builderApi = {
  list: (params?: { page?: number; page_size?: number; visibility?: Visibility; name?: string }) =>
    apiClient.get<any, PaginatedResponse<AgentConfig>>('/api/v1/builder/configs', { params }),

  get: (id: string) =>
    apiClient.get<any, DataResponse<AgentConfig>>(`/api/v1/builder/configs/${id}`),

  create: (data: CreateAgentConfigRequest) =>
    apiClient.post<any, DataResponse<AgentConfig>>('/api/v1/builder/configs', data),

  update: (id: string, data: Partial<CreateAgentConfigRequest>) =>
    apiClient.put<any, DataResponse<AgentConfig>>(`/api/v1/builder/configs/${id}`, data),

  delete: (id: string) =>
    apiClient.delete<any, DataResponse<{ ok: boolean }>>(`/api/v1/builder/configs/${id}`),

  publish: (id: string, data: { visibility?: Visibility; category_id?: string }) =>
    apiClient.post<any, DataResponse<{ ok: boolean }>>(`/api/v1/builder/configs/${id}/publish`, data),

  duplicate: (id: string) =>
    apiClient.post<any, DataResponse<AgentConfig>>(`/api/v1/builder/configs/${id}/duplicate`),

  getVersions: (id: string) =>
    apiClient.get<any, DataResponse<Array<{ version: number; updated_at: string }>>>(`/api/v1/builder/configs/${id}/versions`),

  preview: (id: string) =>
    apiClient.post<any, DataResponse<{ agent_id: string; expires_at: string }>>(`/api/v1/builder/configs/${id}/preview`),

  validate: (data: Record<string, unknown>) =>
    apiClient.post<any, DataResponse<ConfigValidationResult>>('/api/v1/builder/configs/validate', data),

  importConfig: (data: { content: string; format?: 'yaml' | 'json' }) =>
    apiClient.post<any, DataResponse<AgentConfig>>('/api/v1/builder/configs/import', data),

  exportConfig: (id: string, params?: { format?: 'yaml' | 'json' }) =>
    apiClient.get<any, DataResponse<{ content: string; format: string }>>(`/api/v1/builder/configs/${id}/export`, { params }),
};
