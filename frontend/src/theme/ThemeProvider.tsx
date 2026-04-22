import { useEffect, type ReactNode } from 'react';
import { ConfigProvider } from 'antd';
import { useSyncExternalStore } from 'react';
import { useThemeStore } from '@/store/themeStore';
import lightTheme from './lightTheme';
import darkTheme from './darkTheme';

const cssVarsMap = {
  light: {
    '--oh-bg': '#FAF6F0',
    '--oh-surface': '#FFFFFF',
    '--oh-text': '#2D2318',
    '--oh-text-secondary': '#7C6F5B',
    '--oh-border': '#E8E0D4',
    '--oh-primary': '#E8764B',
    '--oh-primary-hover': '#D4682F',
    '--oh-primary-bg': 'rgba(232, 118, 75, 0.08)',
  },
  dark: {
    '--oh-bg': '#0D1117',
    '--oh-surface': '#161B22',
    '--oh-text': '#E6EDF3',
    '--oh-text-secondary': '#8B949E',
    '--oh-border': '#30363D',
    '--oh-primary': '#58A6FF',
    '--oh-primary-hover': '#79B8FF',
    '--oh-primary-bg': 'rgba(88, 166, 255, 0.1)',
  },
} as const;

function applyCssVars(theme: 'light' | 'dark') {
  const vars = cssVarsMap[theme];
  const root = document.documentElement;
  for (const [key, value] of Object.entries(vars)) {
    root.style.setProperty(key, value);
  }
}

function subscribe(cb: () => void) {
  return useThemeStore.subscribe(cb);
}

function getSnapshot() {
  return useThemeStore.getState().theme;
}

function getServerSnapshot() {
  return 'light' as const;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    applyCssVars(theme);
  }, [theme]);

  return (
    <ConfigProvider theme={theme === 'dark' ? darkTheme : lightTheme}>
      {children}
    </ConfigProvider>
  );
}

export default ThemeProvider;
