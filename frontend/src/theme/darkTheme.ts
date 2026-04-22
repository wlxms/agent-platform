import { theme } from 'antd';
import type { ThemeConfig } from 'antd';

const darkTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,

  token: {
    colorPrimary: '#58A6FF',
    colorPrimaryHover: '#79B8FF',
    colorPrimaryActive: '#388BFD',
    colorPrimaryBg: 'rgba(88, 166, 255, 0.1)',
    colorBgContainer: '#161B22',
    colorBgElevated: '#1C2128',
    colorBgLayout: '#0D1117',
    colorText: '#E6EDF3',
    colorTextSecondary: '#8B949E',
    colorTextTertiary: '#6E7681',
    colorBorder: '#30363D',
    colorBorderSecondary: '#21262D',
    colorSuccess: '#3FB950',
    colorWarning: '#D29922',
    colorError: '#F85149',
    colorInfo: '#58A6FF',
    borderRadius: 10,
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: 14,
    lineHeight: 1.6,
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.3)',
    boxShadowSecondary: '0 4px 12px 0 rgba(0, 0, 0, 0.3)',
  },

  components: {
    Button: {
      borderRadius: 8,
    },
    Card: {
      borderRadius: 14,
    },
    Table: {
      headerBg: '#1C2128',
      rowHoverBg: 'rgba(88, 166, 255, 0.06)',
    },
    Menu: {
      itemBorderRadius: 8,
    },
    Input: {
      borderRadius: 8,
    },
    Modal: {
      borderRadius: 14,
    },
    Tag: {
      borderRadiusSM: 6,
    },
  },
};

export default darkTheme;
