import type { ThemeConfig } from 'antd';

const lightTheme: ThemeConfig = {
  algorithm: undefined,

  token: {
    colorPrimary: '#E8764B',
    colorPrimaryHover: '#D4682F',
    colorPrimaryActive: '#C05A23',
    colorPrimaryBg: 'rgba(232, 118, 75, 0.08)',
    colorBgContainer: '#FFFFFF',
    colorBgElevated: '#FFFFFF',
    colorBgLayout: '#FAF6F0',
    colorText: '#2D2318',
    colorTextSecondary: '#7C6F5B',
    colorTextTertiary: '#A99E90',
    colorBorder: '#E8E0D4',
    colorBorderSecondary: '#F0EBE3',
    colorSuccess: '#4CAF50',
    colorWarning: '#FF9800',
    colorError: '#E53935',
    colorInfo: '#42A5F5',
    borderRadius: 10,
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: 14,
    lineHeight: 1.6,
    boxShadow: '0 1px 3px 0 rgba(45, 35, 24, 0.06)',
    boxShadowSecondary: '0 4px 12px 0 rgba(45, 35, 24, 0.06)',
  },

  components: {
    Button: {
      borderRadius: 8,
    },
    Card: {
      borderRadius: 14,
    },
    Table: {
      headerBg: '#FAF6F0',
      rowHoverBg: 'rgba(232, 118, 75, 0.04)',
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

export default lightTheme;
