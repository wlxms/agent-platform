import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { message } from 'antd';
import { useAuthStore } from '@/store/authStore';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_GATEWAY_URL || '',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

let isRefreshing = false;
let pendingRequests: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processPendingRequests(token: string) {
  pendingRequests.forEach(({ resolve }) => resolve(token));
  pendingRequests = [];
}

function rejectPendingRequests(err: unknown) {
  pendingRequests.forEach(({ reject }) => reject(err));
  pendingRequests = [];
}

// Request interceptor: attach JWT token
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: unwrap data, handle 401 refresh, map error codes
apiClient.interceptors.response.use(
  (response) => response.data,
  async (error: AxiosError) => {
    const status = error.response?.status;
    const originalConfig = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // 401 handling with token refresh
    if (status === 401 && !originalConfig._retry) {
      originalConfig._retry = true;

      if (!isRefreshing) {
        isRefreshing = true;
        const refreshToken = useAuthStore.getState().refreshToken;

        try {
          const res = await axios.post(
            `${apiClient.defaults.baseURL}/api/v1/auth/refresh`,
            { refresh_token: refreshToken },
            { headers: { 'Content-Type': 'application/json' } },
          );

          const { token: newToken, refresh_token: newRefreshToken } = res.data.data ?? res.data;
          const store = useAuthStore.getState();
          store.setToken(newToken);
          if (newRefreshToken) {
            store.setRefreshToken(newRefreshToken);
          }

          processPendingRequests(newToken);
          return apiClient(originalConfig);
        } catch (refreshError) {
          rejectPendingRequests(refreshError);
          useAuthStore.getState().logout();
          window.location.href = '/login';
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }

      // Already refreshing — queue this request
      return new Promise((resolve, reject) => {
        pendingRequests.push({
          resolve: (newToken: string) => {
            originalConfig.headers.Authorization = `Bearer ${newToken}`;
            resolve(apiClient(originalConfig));
          },
          reject,
        });
      });
    }

    // Map error codes to UI actions
    if (error.response?.data && typeof error.response.data === 'object') {
      const body = error.response.data as Record<string, unknown>;
      const code = body.code as string | undefined;
      const errorMsg = (body.message as string) || '请求失败';

      switch (code) {
        case 'UNAUTHORIZED':
          window.location.href = '/login';
          break;
        case 'FORBIDDEN':
          message.warning('无权限访问');
          break;
        case 'QUOTA_EXCEEDED':
          message.warning('已达到配额上限');
          break;
        case 'RATE_LIMITED':
          message.warning('请求过于频繁，请稍后重试');
          break;
        case 'VALIDATION_ERROR':
          return Promise.reject({ ...error, details: body.details });
        default:
          message.error(errorMsg);
          break;
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
