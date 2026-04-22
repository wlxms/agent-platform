import { useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Layout, Dropdown, Avatar, Space } from 'antd';
import { SunOutlined, MoonOutlined, UserOutlined, LogoutOutlined } from '@ant-design/icons';
import { useAuthStore } from '@/store/authStore';
import { useTheme } from '@/hooks/useTheme';
import type { MenuProps } from 'antd';

const { Header: AntHeader } = Layout;

const roleLabelMap: Record<string, string> = {
  super_admin: '超级管理员',
  org_admin: '组织管理员',
  team_admin: '团队管理员',
  user: '普通用户',
};

const routeTitleMap: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/agents': 'Agent 管理',
  '/market': 'Marketplace',
  '/builder': 'Agent Builder',
  '/billing': 'Billing',
  '/org': 'Organization',
  '/approvals': 'Approvals',
  '/memory': 'Memory',
};

interface HeaderProps {
  collapsed: boolean;
}

export default function Header({ collapsed }: HeaderProps) {
  const { theme, toggleTheme } = useTheme();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const location = useLocation();
  const navigate = useNavigate();

  const pageTitle = useMemo(() => {
    const path = location.pathname;
    const match = Object.entries(routeTitleMap)
      .sort(([, a], [, b]) => b.length - a.length)
      .find(([route]) => path === route || path.startsWith(route + '/'));
    return match?.[1] ?? 'AgentPlatform';
  }, [location.pathname]);

  const isDark = theme === 'dark';

  const themeMenuItems: MenuProps['items'] = [
    {
      key: 'light',
      icon: <SunOutlined />,
      label: '☀️ 浅色模式',
      onClick: () => { if (isDark) toggleTheme(); },
    },
    {
      key: 'dark',
      icon: <MoonOutlined />,
      label: '🌙 深色模式',
      onClick: () => { if (!isDark) toggleTheme(); },
    },
  ];

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'info',
      icon: <UserOutlined />,
      label: (
        <span style={{ color: 'var(--oh-text)' }}>
          {user?.username ?? '未知用户'}
          <br />
          <span style={{ fontSize: 12, color: 'var(--oh-text-secondary)' }}>
            {user?.role ? roleLabelMap[user.role] ?? user.role : ''}
          </span>
        </span>
      ),
      disabled: true,
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
      onClick: () => {
        logout();
        navigate('/login');
      },
    },
  ];

  return (
    <AntHeader
      style={{
        height: 56,
        lineHeight: '56px',
        padding: '0 24px',
        background: 'var(--oh-surface)',
        borderBottom: '1px solid var(--oh-border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 9,
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.06)',
        marginLeft: collapsed ? 80 : 240,
        transition: 'margin-left 0.2s cubic-bezier(0.2, 0, 0, 1)',
      }}
    >
      {/* Left: page title */}
      <h2
        style={{
          margin: 0,
          fontSize: 16,
          fontWeight: 600,
          color: 'var(--oh-text)',
          letterSpacing: '-0.2px',
        }}
      >
        {pageTitle}
      </h2>

      {/* Right: theme switch + user menu */}
      <Space size={12} align="center">
        <Dropdown
          menu={{ items: themeMenuItems, selectedKeys: [theme] }}
          placement="bottomRight"
          trigger={['click']}
        >
          <button
            aria-label="切换主题"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 36,
              height: 36,
              border: '1px solid var(--oh-border)',
              borderRadius: 8,
              background: 'var(--oh-surface)',
              color: 'var(--oh-text-secondary)',
              cursor: 'pointer',
              fontSize: 16,
              transition: 'border-color 0.2s, color 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--oh-primary)';
              e.currentTarget.style.color = 'var(--oh-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--oh-border)';
              e.currentTarget.style.color = 'var(--oh-text-secondary)';
            }}
          >
            {isDark ? <MoonOutlined /> : <SunOutlined />}
          </button>
        </Dropdown>

        <Dropdown
          menu={{ items: userMenuItems }}
          placement="bottomRight"
          trigger={['click']}
        >
          <Space
            style={{
              cursor: 'pointer',
              padding: '4px 8px',
              borderRadius: 8,
              transition: 'background 0.2s',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = 'var(--oh-primary-bg)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = 'transparent';
            }}
          >
            <Avatar
              size={32}
              style={{
                background: 'var(--oh-primary)',
                color: '#fff',
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              {user?.username?.charAt(0).toUpperCase() ?? 'U'}
            </Avatar>
          </Space>
        </Dropdown>
      </Space>
    </AntHeader>
  );
}
