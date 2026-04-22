import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Card, Form, Input, Button, Typography, message, Space } from 'antd';
import { RobotOutlined, KeyOutlined, EyeInvisibleOutlined, EyeOutlined } from '@ant-design/icons';
import { useAuthStore, type User } from '@/store/authStore';
import { authApi } from '@/api/auth';

interface LoginFormValues {
  api_key: string;
}

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | undefined)?.from?.pathname || '/dashboard';

  const handleSubmit = async (values: LoginFormValues) => {
    setLoading(true);
    try {
      const res = await authApi.login(values);
      const store = useAuthStore.getState();
      store.setToken(res.data.token);
      store.setRefreshToken(res.data.refresh_token);
      store.setUser(res.data.user as User);
      message.success('登录成功');
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { code?: string } } };
      const code = axiosErr?.response?.data?.code;
      if (code === 'UNAUTHORIZED' || code === 'VALIDATION_ERROR') {
        message.error('API Key 无效，请检查后重试');
      } else {
        message.error('登录失败，请稍后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--oh-bg)',
      padding: 24,
    }}>
      <Card
        style={{
          width: 420,
          borderRadius: 14,
          boxShadow: 'var(--oh-shadow-md, 0 4px 12px rgba(0,0,0,0.08))',
          background: 'var(--oh-surface)',
        }}
        styles={{ body: { padding: '48px 40px' } }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%', textAlign: 'center' }}>
          <div>
            <RobotOutlined style={{ fontSize: 48, color: 'var(--oh-primary)' }} />
            <Typography.Title level={3} style={{ margin: '12px 0 4px', color: 'var(--oh-text)' }}>
              AgentPlatform
            </Typography.Title>
            <Typography.Text type="secondary">
              输入 API Key 登录管理控制台
            </Typography.Text>
          </div>

          <Form<LoginFormValues>
            layout="vertical"
            onFinish={handleSubmit}
            autoComplete="off"
          >
            <Form.Item
              name="api_key"
              rules={[{ required: true, message: '请输入 API Key' }]}
            >
              <Input.Password
                prefix={<KeyOutlined />}
                placeholder="请输入 API Key"
                size="large"
                iconRender={(visible) => visible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                style={{ borderRadius: 8 }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
                size="large"
                style={{ borderRadius: 8, height: 44, fontWeight: 500 }}
              >
                {loading ? '登录中...' : '登 录'}
              </Button>
            </Form.Item>
          </Form>
        </Space>
      </Card>
    </div>
  );
}
