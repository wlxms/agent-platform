import apiClient from './client';
import type {
  MemoryAsset, MemoryTreeNode,
  DataResponse,
} from '@/types';

export const memoryApi = {
  getAssets: (params?: { path?: string }) =>
    apiClient.get<any, DataResponse<MemoryTreeNode[]>>('/api/v1/memory/assets', { params }),

  getAsset: (path: string) =>
    apiClient.get<any, DataResponse<MemoryAsset>>(`/api/v1/memory/assets/${encodeURIComponent(path)}`),

  uploadAsset: (path: string, data: FormData | { content: string }) =>
    apiClient.put<any, DataResponse<{ ok: boolean }>>(`/api/v1/memory/assets/${encodeURIComponent(path)}`, data),

  deleteAsset: (path: string) =>
    apiClient.delete<any, DataResponse<{ ok: boolean }>>(`/api/v1/memory/assets/${encodeURIComponent(path)}`),

  search: (params: { keyword: string }) =>
    apiClient.get<any, DataResponse<MemoryAsset[]>>('/api/v1/memory/search', { params }),
};
