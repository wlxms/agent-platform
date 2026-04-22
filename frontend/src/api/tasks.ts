import apiClient from './client';
import type { TaskInfo, DataResponse } from '@/types';

export const tasksApi = {
  getStatus: (taskId: string) =>
    apiClient.get<any, DataResponse<TaskInfo>>(`/api/v1/tasks/${taskId}`),
};
