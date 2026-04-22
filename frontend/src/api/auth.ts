import apiClient from './client';

export interface LoginRequest {
  api_key: string;
}

export interface LoginResponse {
  token: string;
  refresh_token: string;
  user: {
    id: string;
    username: string;
    role: string;
    org_id: string;
  };
}

export interface RefreshResponse {
  token: string;
  refresh_token: string;
}

export interface UserInfo {
  id: string;
  username: string;
  role: string;
  org_id: string;
}

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<unknown, { data: LoginResponse }>('/api/v1/auth/login', data),

  refresh: () =>
    apiClient.post<unknown, { data: RefreshResponse }>('/api/v1/auth/refresh'),

  logout: () =>
    apiClient.post('/api/v1/auth/logout'),

  me: () =>
    apiClient.get<unknown, { data: UserInfo }>('/api/v1/auth/me'),
};
