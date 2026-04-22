import apiClient from './client';
import type {
  BillingSummary, BillingRecord, SetBudgetRequest,
  PaginatedResponse, DataResponse,
} from '@/types';

export interface Budget {
  threshold: number;
  alert_rules?: Array<Record<string, unknown>>;
}

export const billingApi = {
  getSummary: (params?: { period?: string; org_id?: string }) =>
    apiClient.get<any, DataResponse<BillingSummary>>('/api/v1/billing/usage/summary', { params }),

  getRecords: (params?: {
    page?: number; page_size?: number;
    agent_id?: string; model?: string;
    created_after?: string; created_before?: string;
  }) =>
    apiClient.get<any, PaginatedResponse<BillingRecord>>('/api/v1/billing/usage/records', { params }),

  exportCsv: (params?: {
    agent_id?: string; model?: string;
    created_after?: string; created_before?: string;
  }) =>
    apiClient.get<any, Blob>('/api/v1/billing/export', { params, responseType: 'blob' }),

  getBudget: (params?: { org_id?: string }) =>
    apiClient.get<any, DataResponse<Budget>>('/api/v1/billing/budget', { params }),

  setBudget: (data: SetBudgetRequest) =>
    apiClient.put<any, DataResponse<Budget>>('/api/v1/billing/budget', data),
};
