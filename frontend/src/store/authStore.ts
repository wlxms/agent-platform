import { create } from 'zustand';

interface User {
  id: string;
  username: string;
  role: 'super_admin' | 'org_admin' | 'team_admin' | 'user';
  org_id: string;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  setRefreshToken: (token: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('oh-token') || null,
  refreshToken: localStorage.getItem('oh-refresh-token') || null,
  user: null,
  isAuthenticated: !!localStorage.getItem('oh-token'),
  setToken: (token) => {
    localStorage.setItem('oh-token', token);
    set({ token, isAuthenticated: true });
  },
  setRefreshToken: (token) => {
    localStorage.setItem('oh-refresh-token', token);
    set({ refreshToken: token });
  },
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem('oh-token');
    localStorage.removeItem('oh-refresh-token');
    set({ token: null, refreshToken: null, user: null, isAuthenticated: false });
  },
}));

export type { User };
