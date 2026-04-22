import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Layout } from 'antd';
import Sidebar from './Sidebar';
import Header from './Header';

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);

  const siderWidth = collapsed ? 80 : 240;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />

      <Layout
        style={{
          marginLeft: siderWidth,
          transition: 'margin-left 0.2s cubic-bezier(0.2, 0, 0, 1)',
          background: 'var(--oh-bg)',
        }}
      >
        <Header collapsed={collapsed} />

        <Layout.Content
          style={{
            padding: 24,
            background: 'var(--oh-bg)',
            minHeight: 'calc(100vh - 56px)',
          }}
        >
          <Outlet />
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
