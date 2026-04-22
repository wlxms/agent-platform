import apiClient from './client';
import type {
  Template, Skill, McpServerItem, MarketCategory,
  PaginatedResponse, DataResponse,
} from '@/types';

export const marketApi = {
  getTemplates: (params?: { category?: string; keyword?: string; page?: number; page_size?: number }) =>
    apiClient.get<any, PaginatedResponse<Template>>('/api/v1/market/templates', { params }),

  getTemplate: (id: string) =>
    apiClient.get<any, DataResponse<Template>>(`/api/v1/market/templates/${id}`),

  getSkills: (params?: { keyword?: string; page?: number; page_size?: number }) =>
    apiClient.get<any, PaginatedResponse<Skill>>('/api/v1/market/skills', { params }),

  getSkill: (id: string) =>
    apiClient.get<any, DataResponse<Skill>>(`/api/v1/market/skills/${id}`),

  getMcps: (params?: { keyword?: string; page?: number; page_size?: number }) =>
    apiClient.get<any, PaginatedResponse<McpServerItem>>('/api/v1/market/mcps', { params }),

  getMcp: (id: string) =>
    apiClient.get<any, DataResponse<McpServerItem>>(`/api/v1/market/mcps/${id}`),

  getCategories: () =>
    apiClient.get<any, DataResponse<MarketCategory[]>>('/api/v1/market/categories'),
};
