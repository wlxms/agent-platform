import apiClient from './client';
import type {
  Approval, ApprovalStatus, RejectApprovalRequest,
  PaginatedResponse, DataResponse,
} from '@/types';

export const approvalsApi = {
  list: (params?: { status?: ApprovalStatus; org_id?: string; page?: number; page_size?: number }) =>
    apiClient.get<any, PaginatedResponse<Approval>>('/api/v1/approvals', { params }),

  approve: (id: string) =>
    apiClient.post<any, DataResponse<{ ok: boolean; status: string }>>(`/api/v1/approvals/${id}/approve`),

  reject: (id: string, data: RejectApprovalRequest) =>
    apiClient.post<any, DataResponse<{ ok: boolean; status: string }>>(`/api/v1/approvals/${id}/reject`, data),

  getHistory: (params?: { org_id?: string; page?: number; page_size?: number }) =>
    apiClient.get<any, PaginatedResponse<Approval>>('/api/v1/approvals/history', { params }),
};
