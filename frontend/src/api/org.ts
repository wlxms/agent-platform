import apiClient from './client';
import type {
  OrgNode, OrgDetail, OrgMember, AddMemberRequest,
  ApiKey, CreateApiKeyRequest, CreateApiKeyResponse,
  Permission, Role, UpdateRoleRequest,
  UserRole, PaginatedResponse, DataResponse,
} from '@/types';

export const orgApi = {
  getTree: (params?: { depth?: number }) =>
    apiClient.get<any, DataResponse<OrgNode[]>>('/api/v1/org/tree', { params }),

  get: (id: string) =>
    apiClient.get<any, DataResponse<OrgDetail>>(`/api/v1/org/${id}`),

  create: (data: { name: string; parent_id?: string }) =>
    apiClient.post<any, DataResponse<OrgNode>>('/api/v1/org', data),

  getMembers: (orgId: string, params?: { page?: number; page_size?: number }) =>
    apiClient.get<any, PaginatedResponse<OrgMember>>(`/api/v1/org/${orgId}/members`, { params }),

  addMember: (orgId: string, data: AddMemberRequest) =>
    apiClient.post<any, DataResponse<OrgMember>>(`/api/v1/org/${orgId}/members`, data),

  removeMember: (orgId: string, userId: string) =>
    apiClient.delete<any, DataResponse<{ ok: boolean }>>(`/api/v1/org/${orgId}/members/${userId}`),

  updateMemberRole: (orgId: string, userId: string, data: { role: UserRole }) =>
    apiClient.put<any, DataResponse<OrgMember>>(`/api/v1/org/${orgId}/members/${userId}`, data),

  getApiKeys: (orgId: string, params?: { page?: number; page_size?: number }) =>
    apiClient.get<any, PaginatedResponse<ApiKey>>(`/api/v1/org/${orgId}/api-keys`, { params }),

  createApiKey: (orgId: string, data: CreateApiKeyRequest) =>
    apiClient.post<any, DataResponse<CreateApiKeyResponse>>(`/api/v1/org/${orgId}/api-keys`, data),

  revokeApiKey: (orgId: string, keyId: string) =>
    apiClient.delete<any, DataResponse<{ ok: boolean }>>(`/api/v1/org/${orgId}/api-keys/${keyId}`),

  renewApiKey: (orgId: string, keyId: string, data?: { expires_days?: number }) =>
    apiClient.post<any, DataResponse<ApiKey>>(`/api/v1/org/${orgId}/api-keys/${keyId}/renew`, data),

  getPermissions: () =>
    apiClient.get<any, DataResponse<Permission[]>>('/api/v1/permissions'),

  getRoles: () =>
    apiClient.get<any, DataResponse<Role[]>>('/api/v1/roles'),

  updateRole: (roleId: string, data: UpdateRoleRequest) =>
    apiClient.put<any, DataResponse<Role>>(`/api/v1/roles/${roleId}`, data),
};
