import { useThemeStore } from '@/store/themeStore';

export function useTheme() {
  const { theme, setTheme, toggleTheme } = useThemeStore();
  const isDark = theme === 'dark';
  return { theme, setTheme, toggleTheme, isDark } as const;
}
