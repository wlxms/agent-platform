import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Breadcrumb, Tag, Button, Typography, Descriptions,
  Row, Col, Statistic, Divider, Spin, message, Space,
} from 'antd';
import {
  ArrowLeftOutlined, ThunderboltOutlined,
  UserOutlined, EyeOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { marketApi } from '@/api/market';
import type { Template } from '@/types';

const { Title, Paragraph, Text } = Typography;

export default function TemplateDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [template, setTemplate] = useState<Template | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const fetchTemplate = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setNotFound(false);
    try {
      const res = await marketApi.getTemplate(id);
      setTemplate(res.data);
    } catch (err: any) {
      if (err?.response?.status === 404 || err?.response?.data?.code === 'NOT_FOUND') {
        setNotFound(true);
      } else {
        message.error('加载模板详情失败');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 120 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!id || notFound) {
    return (
      <Card style={{ borderRadius: 12, border: `1px solid var(--oh-border)` }}>
        <Title level={4}>模板未找到</Title>
        <Text type="secondary">请求的模板不存在或已被删除。</Text>
        <Button style={{ marginTop: 16 }} onClick={() => navigate('/market')}>
          返回市场
        </Button>
      </Card>
    );
  }

  if (!template) return null;

  const resSpec = template.resource_spec;
  const hasResourceSpec = resSpec && (resSpec.cpu || resSpec.memory || resSpec.gpu);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Breadcrumb
        items={[
          { title: <a onClick={() => navigate('/market')}>市场</a> },
          { title: template.name },
        ]}
        style={{ marginBottom: 24 }}
      />

      <Row gutter={[24, 24]}>
        {/* ── Left Column ── */}
        <Col xs={24} lg={16}>
          {/* Header */}
          <Card
            style={{ borderRadius: 12, border: `1px solid var(--oh-border)`, marginBottom: 24 }}
            styles={{ body: { padding: 24 } }}
          >
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Space align="center" wrap size={8}>
                <Title level={2} style={{ margin: 0, color: 'var(--oh-text)' }}>
                  {template.name}
                </Title>
                {template.category_name && (
                  <Tag color="blue">{template.category_name}</Tag>
                )}
              </Space>

              <Space size={16} wrap style={{ color: 'var(--oh-text-secondary)' }}>
                {template.author && (
                  <Text>
                    <UserOutlined style={{ marginRight: 4 }} />
                    {template.author}
                  </Text>
                )}
                <Text>
                  <EyeOutlined style={{ marginRight: 4 }} />
                  {template.usage_count} 次使用
                </Text>
                <Text>
                  <ClockCircleOutlined style={{ marginRight: 4 }} />
                  创建于 {dayjs(template.created_at).format('YYYY-MM-DD')}
                </Text>
                {template.updated_at !== template.created_at && (
                  <Text>
                    更新于 {dayjs(template.updated_at).format('YYYY-MM-DD')}
                  </Text>
                )}
              </Space>
            </Space>
          </Card>

          {/* Description */}
          <Card
            title="描述"
            style={{ borderRadius: 12, border: `1px solid var(--oh-border)`, marginBottom: 24 }}
            styles={{ body: { padding: 24 } }}
          >
            <Paragraph style={{ color: 'var(--oh-text)', marginBottom: template.scenario ? 16 : 0 }}>
              {template.description}
            </Paragraph>
            {template.scenario && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <Title level={5} style={{ color: 'var(--oh-text)', marginBottom: 8 }}>适用场景</Title>
                <Paragraph style={{ color: 'var(--oh-text-secondary)' }}>
                  {template.scenario}
                </Paragraph>
              </>
            )}
          </Card>

          {/* Pre-configured Skills */}
          {template.skills.length > 0 && (
            <Card
              title="预置技能"
              style={{ borderRadius: 12, border: `1px solid var(--oh-border)`, marginBottom: 24 }}
              styles={{ body: { padding: 24 } }}
            >
              <Space size={[8, 8]} wrap>
                {template.skills.map((s) => (
                  <Tag key={s.id} style={{ borderRadius: 6, padding: '2px 10px', cursor: 'pointer' }}>
                    <ThunderboltOutlined style={{ marginRight: 4 }} />
                    {s.name}
                  </Tag>
                ))}
              </Space>
            </Card>
          )}

          {/* Pre-configured MCP Servers */}
          {template.mcp_servers.length > 0 && (
            <Card
              title="预置 MCP 服务"
              style={{ borderRadius: 12, border: `1px solid var(--oh-border)`, marginBottom: 24 }}
              styles={{ body: { padding: 24 } }}
            >
              <Space size={[8, 8]} wrap>
                {template.mcp_servers.map((m) => (
                  <Tag key={m.id} style={{ borderRadius: 6, padding: '2px 10px', cursor: 'pointer' }}>
                    {m.name}
                    {m.transport && (
                      <Text type="secondary" style={{ marginLeft: 4, fontSize: 11 }}>
                        [{m.transport.toUpperCase()}]
                      </Text>
                    )}
                  </Tag>
                ))}
              </Space>
            </Card>
          )}

          {/* Resource Spec */}
          {hasResourceSpec && (
            <Card
              title="资源需求"
              style={{ borderRadius: 12, border: `1px solid var(--oh-border)` }}
              styles={{ body: { padding: 24 } }}
            >
              <Descriptions
                column={{ xs: 1, sm: 2, lg: 3 }}
                bordered
                size="small"
                labelStyle={{ fontWeight: 500, color: 'var(--oh-text-secondary)', backgroundColor: 'var(--oh-surface)' }}
                contentStyle={{ backgroundColor: 'var(--oh-surface)' }}
              >
                {resSpec.cpu && <Descriptions.Item label="CPU">{resSpec.cpu}</Descriptions.Item>}
                {resSpec.memory && <Descriptions.Item label="内存">{resSpec.memory}</Descriptions.Item>}
                {resSpec.gpu && <Descriptions.Item label="GPU">{resSpec.gpu}</Descriptions.Item>}
              </Descriptions>
            </Card>
          )}
        </Col>

        {/* ── Right Column ── */}
        <Col xs={24} lg={8}>
          <div style={{ position: 'sticky', top: 24 }}>
            <Card
              style={{ borderRadius: 12, border: `1px solid var(--oh-border)`, marginBottom: 24 }}
              styles={{ body: { padding: 24, display: 'flex', flexDirection: 'column', gap: 16 } }}
            >
              <Button
                type="primary"
                size="large"
                block
                onClick={() => navigate(`/agents/new?template_id=${id}`)}
                style={{ height: 44, fontWeight: 600 }}
              >
                使用此模板
              </Button>
              <Button
                size="large"
                block
                icon={<ArrowLeftOutlined />}
                onClick={() => navigate('/market')}
                style={{ height: 44 }}
              >
                返回市场
              </Button>
            </Card>

            <Card
              title="作者"
              style={{ borderRadius: 12, border: `1px solid var(--oh-border)` }}
              styles={{
                body: { padding: 24 },
                header: { borderBottom: `1px solid var(--oh-border)` },
              }}
            >
              <Space direction="vertical" size={8}>
                <Space>
                  <UserOutlined style={{ fontSize: 20, color: 'var(--oh-text-secondary)' }} />
                  <Text strong style={{ color: 'var(--oh-text)', fontSize: 16 }}>
                    {template.author || '未知'}
                  </Text>
                </Space>
                <Statistic
                  title="模板使用量"
                  value={template.usage_count}
                  suffix="次"
                  valueStyle={{ color: 'var(--oh-text)', fontSize: 20 }}
                />
              </Space>
            </Card>
          </div>
        </Col>
      </Row>
    </div>
  );
}
