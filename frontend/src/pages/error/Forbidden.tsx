import { useNavigate } from 'react-router-dom';
import { LockOutlined } from '@ant-design/icons';
import { Button } from 'antd';

export default function Forbidden() {
  const navigate = useNavigate();

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        backgroundColor: 'var(--oh-bg)',
        color: 'var(--oh-text)',
        gap: '12px',
      }}
    >
      <LockOutlined
        style={{ fontSize: 64, color: 'var(--oh-text-secondary)', marginBottom: 8 }}
      />
      <h1
        style={{
          fontSize: 72,
          fontWeight: 700,
          margin: 0,
          color: 'var(--oh-text)',
          lineHeight: 1,
        }}
      >
        403
      </h1>
      <p
        style={{
          fontSize: 16,
          margin: 0,
          color: 'var(--oh-text-secondary)',
        }}
      >
        无权限访问此页面
      </p>
      <Button type="primary" style={{ marginTop: 16 }} onClick={() => navigate('/dashboard')}>
        返回首页
      </Button>
    </div>
  );
}
