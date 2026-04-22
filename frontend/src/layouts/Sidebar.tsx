import { useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  RobotOutlined,
  ShopOutlined,
  ToolOutlined,
  AccountBookOutlined,
  ApartmentOutlined,
  AuditOutlined,
  CloudServerOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '@/store/authStore';
import type { MenuProps } from 'antd';

const { Sider } = Layout;

interface MenuItem {
  key: string;
  icon: React.ReactNode;
  label: string;
  path: string;
  minRole: 'user' | 'org_admin';
}

const menuConfig: MenuItem[] = [
  { key: 'dashboard', icon: <DashboardOutlined />, label: 'Dashboard', path: '/dashboard', minRole: 'user' },
  { key: 'agents', icon: <RobotOutlined />, label: 'Agent 管理', path: '/agents', minRole: 'user' },
  { key: 'market', icon: <ShopOutlined />, label: 'Marketplace', path: '/market', minRole: 'user' },
  { key: 'builder', icon: <ToolOutlined />, label: 'Agent Builder', path: '/builder', minRole: 'user' },
  { key: 'billing', icon: <AccountBookOutlined />, label: 'Billing', path: '/billing', minRole: 'user' },
  { key: 'org', icon: <ApartmentOutlined />, label: 'Organization', path: '/org', minRole: 'org_admin' },
  { key: 'approvals', icon: <AuditOutlined />, label: 'Approvals', path: '/approvals', minRole: 'org_admin' },
  { key: 'memory', icon: <CloudServerOutlined />, label: 'Memory', path: '/memory', minRole: 'user' },
];

const roleWeight: Record<string, number> = {
  user: 0,
  team_admin: 1,
  org_admin: 2,
  super_admin: 3,
};

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);

  const visibleItems = useMemo(() => {
    const w = user ? (roleWeight[user.role] ?? 0) : 0;
    const minW: Record<string, number> = { user: 0, org_admin: 2 };
    return menuConfig.filter((item) => w >= (minW[item.minRole] ?? 0));
  }, [user]);

  const antItems: MenuProps['items'] = visibleItems.map((item) => ({
    key: item.key,
    icon: item.icon,
    label: item.label,
  }));

  const selectedKey = useMemo(() => {
    const path = location.pathname;
    const match = [...visibleItems].reverse().find((item) => path.startsWith(item.path));
    return match?.key ?? 'dashboard';
  }, [location.pathname, visibleItems]);

  const onMenuClick: MenuProps['onClick'] = ({ key }) => {
    const item = visibleItems.find((m) => m.key === key);
    if (item) navigate(item.path);
  };

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      trigger={null}
      width={240}
      collapsedWidth={80}
      style={{
        background: 'var(--oh-surface)',
        borderRight: '1px solid var(--oh-border)',
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        zIndex: 10,
        transition: 'width 0.2s cubic-bezier(0.2, 0, 0, 1)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Logo */}
      <div
        style={{
          height: 56,
          display: 'flex',
          alignItems: 'center',
          padding: collapsed ? '0 0' : '0 20px',
          justifyContent: collapsed ? 'center' : 'flex-start',
          borderBottom: '1px solid var(--oh-border)',
          flexShrink: 0,
          overflow: 'hidden',
          whiteSpace: 'nowrap',
        }}
      >
        <RobotOutlined
          style={{
            fontSize: 24,
            color: 'var(--oh-primary)',
            flexShrink: 0,
          }}
        />
        {!collapsed && (
          <span
            style={{
              marginLeft: 10,
              fontSize: 16,
              fontWeight: 700,
              color: 'var(--oh-text)',
              letterSpacing: '-0.3px',
            }}
          >
            AgentPlatform
          </span>
        )}
      </div>

      {/* Menu */}
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        items={antItems}
        onClick={onMenuClick}
        style={{
          flex: 1,
          borderRight: 'none',
          background: 'transparent',
          paddingTop: 8,
        }}
      />

      {/* Collapse toggle */}
      <div
        style={{
          borderTop: '1px solid var(--oh-border)',
          padding: '12px 0',
          display: 'flex',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <button
          onClick={onToggle}
          aria-label={collapsed ? '展开侧栏' : '收起侧栏'}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 40,
            height: 40,
            border: 'none',
            borderRadius: 8,
            background: 'var(--oh-primary-bg)',
            color: 'var(--oh-primary)',
            cursor: 'pointer',
            fontSize: 16,
            transition: 'background 0.2s, transform 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--oh-primary)';
            e.currentTarget.style.color = '#fff';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--oh-primary-bg)';
            e.currentTarget.style.color = 'var(--oh-primary)';
          }}
        >
          {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </button>
      </div>
    </Sider>
  );
}
