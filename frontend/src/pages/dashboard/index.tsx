import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Card, Tabs, Table, Statistic, Row, Col, Badge, Progress,
  Button, Typography, Spin, Empty, Tooltip, theme,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, DeleteOutlined,
  DashboardOutlined, TeamOutlined, SettingOutlined,
  CheckCircleOutlined, WarningOutlined, CloseCircleOutlined,
} from '@ant-design/icons';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import {
  GridComponent, TooltipComponent, LegendComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import dayjs from 'dayjs';
import { agentsApi } from '@/api/agents';
import { billingApi } from '@/api/billing';
import { useAuthStore } from '@/store/authStore';
import type { AgentInstance, AgentStatus, BillingSummary } from '@/types';
import type { ColumnsType } from 'antd/es/table';

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

const { Title, Text } = Typography;

type ServiceStatus = 'healthy' | 'degraded' | 'down';

interface ServiceHealth {
  name: string;
  status: ServiceStatus;
  uptime: string;
}

const MOCK_SERVICES: ServiceHealth[] = [
  { name: 'Gateway', status: 'healthy', uptime: '99.97%' },
  { name: 'Auth', status: 'healthy', uptime: '99.99%' },
  { name: 'Host', status: 'degraded', uptime: '98.50%' },
  { name: 'Scheduler', status: 'healthy', uptime: '99.95%' },
  { name: 'Billing', status: 'healthy', uptime: '99.90%' },
  { name: 'Market', status: 'down', uptime: '95.20%' },
];

const STATUS_BADGE_MAP: Record<AgentStatus, { color: string; text: string }> = {
  ready: { color: 'green', text: '就绪' },
  running: { color: 'blue', text: '运行中' },
  creating: { color: 'gold', text: '创建中' },
  seeding: { color: 'gold', text: '初始化' },
  stopping: { color: 'default', text: '停止中' },
  stopped: { color: 'default', text: '已停止' },
  failed: { color: 'red', text: '失败' },
};

const SERVICE_STATUS_ICON: Record<ServiceStatus, { icon: React.ReactNode; color: string }> = {
  healthy: { icon: <CheckCircleOutlined />, color: '#52c41a' },
  degraded: { icon: <WarningOutlined />, color: '#faad14' },
  down: { icon: <CloseCircleOutlined />, color: '#ff4d4f' },
};

// ─── Personal Dashboard ───────────────────────────────────────────

function PersonalDashboard() {
  const { token: themeToken } = theme.useToken();
  const [agents, setAgents] = useState<AgentInstance[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [chartLoading, setChartLoading] = useState(true);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    try {
      const res = await agentsApi.list({ page_size: 10 });
      setAgents(res.items);
      setTotal(res.total);
    } catch {
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSummary = useCallback(async () => {
    setChartLoading(true);
    try {
      const res = await billingApi.getSummary({ period: 'week' });
      setSummary(res.data);
    } catch {
      setSummary(null);
    } finally {
      setChartLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    fetchSummary();
  }, [fetchAgents, fetchSummary]);

  const chartOption = useMemo(() => {
    if (!summary?.daily_trend?.length) return {};
    return {
      tooltip: {
        trigger: 'axis' as const,
        backgroundColor: themeToken.colorBgElevated,
        borderColor: themeToken.colorBorder,
        textStyle: { color: themeToken.colorText },
      },
      grid: { left: 50, right: 20, top: 30, bottom: 30 },
      xAxis: {
        type: 'category',
        data: summary.daily_trend.map((d) => dayjs(d.date).format('MM-DD')),
        axisLine: { lineStyle: { color: themeToken.colorBorderSecondary } },
        axisLabel: { color: themeToken.colorTextSecondary },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        splitLine: { lineStyle: { color: themeToken.colorBorderSecondary } },
        axisLabel: { color: themeToken.colorTextSecondary },
      },
      series: [
        {
          name: '费用',
          type: 'line',
          data: summary.daily_trend.map((d) => d.cost),
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { color: themeToken.colorPrimary, width: 2 },
          itemStyle: { color: themeToken.colorPrimary },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: `${themeToken.colorPrimary}30` },
              { offset: 1, color: `${themeToken.colorPrimary}05` },
            ]),
          },
        },
      ],
    };
  }, [summary, themeToken]);

  const columns: ColumnsType<AgentInstance> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: AgentStatus) => {
        const cfg = STATUS_BADGE_MAP[status] ?? { color: 'default', text: status };
        return <Badge color={cfg.color} text={cfg.text} />;
      },
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      width: 160,
      ellipsis: true,
      render: (_, record) => record.model_config?.model ?? record.model ?? '-',
    },
    {
      title: '最后活跃',
      dataIndex: 'last_active_at',
      key: 'last_active_at',
      width: 170,
      render: (v: string | undefined) =>
        v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_, record) => (
        <span style={{ display: 'flex', gap: 4 }}>
          <Tooltip title="重启">
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => agentsApi.restart(record.id).then(fetchAgents)}
            />
          </Tooltip>
          <Tooltip title="销毁">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => agentsApi.destroy(record.id).then(fetchAgents)}
            />
          </Tooltip>
        </span>
      ),
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card
        title={<Title level={5} style={{ margin: 0 }}>Agent 实例</Title>}
        extra={
          <Button type="primary" icon={<PlusOutlined />}>
            创建实例
          </Button>
        }
      >
        <Spin spinning={loading}>
          <Table<AgentInstance>
            rowKey="id"
            columns={columns}
            dataSource={agents}
            size="middle"
            pagination={false}
            locale={{ emptyText: <Empty description="暂无 Agent 实例" /> }}
          />
          {total > 10 && (
            <div style={{ textAlign: 'center', marginTop: 12 }}>
              <Text type="secondary">共 {total} 个实例，仅显示前 10 个</Text>
            </div>
          )}
        </Spin>
      </Card>

      <Card title={<Title level={5} style={{ margin: 0 }}>近 7 天费用趋势</Title>}>
        <Spin spinning={chartLoading}>
          {summary?.daily_trend?.length ? (
            <ReactEChartsCore
              echarts={echarts}
              option={chartOption}
              style={{ height: 300 }}
              opts={{ renderer: 'canvas' }}
            />
          ) : (
            <Empty description="暂无费用数据" />
          )}
        </Spin>
      </Card>
    </div>
  );
}

// ─── Organization Dashboard ───────────────────────────────────────

function OrganizationDashboard() {
  const { token: themeToken } = theme.useToken();
  const [agents, setAgents] = useState<AgentInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await agentsApi.list({ page_size: 100 });
        setAgents(res.items);
      } catch { /* empty */ } finally {
        setLoading(false);
      }
    })();
    (async () => {
      setSummaryLoading(true);
      try {
        const res = await billingApi.getSummary({ period: 'week' });
        setSummary(res.data);
      } catch { /* empty */ } finally {
        setSummaryLoading(false);
      }
    })();
  }, []);

  const statusCounts = useMemo(() => {
    const counts = { running: 0, idle: 0, total: agents.length };
    for (const a of agents) {
      if (a.status === 'running' || a.status === 'ready') counts.running++;
      else if (a.status === 'stopped') counts.idle++;
    }
    return counts;
  }, [agents]);

  const budgetPercent = useMemo(() => {
    if (!summary || !summary.budget || summary.budget === 0) return 0;
    const spent = summary.budget - (summary.budget_remaining ?? 0);
    return Math.min(100, Math.round((spent / summary.budget) * 100));
  }, [summary]);

  return (
    <Spin spinning={loading || summaryLoading}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Row gutter={16}>
          <Col span={8}>
            <Card><Statistic title="总实例数" value={statusCounts.total} /></Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="运行中"
                value={statusCounts.running}
                valueStyle={{ color: themeToken.colorInfo }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="空闲"
                value={statusCounts.idle}
                valueStyle={{ color: themeToken.colorTextTertiary }}
              />
            </Card>
          </Col>
        </Row>

        <Card title={<Title level={5} style={{ margin: 0 }}>预算概览</Title>}>
          {summary && summary.budget ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <Text>已使用 ¥{((summary.budget ?? 0) - (summary.budget_remaining ?? 0)).toFixed(2)}</Text>
                <Text type="secondary">预算 ¥{summary.budget.toFixed(2)}</Text>
              </div>
              <Progress
                percent={budgetPercent}
                strokeColor={{
                  '0%': themeToken.colorPrimary,
                  '100%': themeToken.colorError,
                }}
                format={(p) => `${p}%`}
              />
            </div>
          ) : (
            <Empty description="暂未设置预算" />
          )}
        </Card>

        <Card title={<Title level={5} style={{ margin: 0 }}>待审批</Title>}>
          <Badge count={0} showZero>
            <Text type="secondary">当前没有待审批的请求</Text>
          </Badge>
        </Card>
      </div>
    </Spin>
  );
}

// ─── System Dashboard ─────────────────────────────────────────────

function SystemDashboard() {
  return (
    <Row gutter={[16, 16]}>
      {MOCK_SERVICES.map((svc) => {
        const cfg = SERVICE_STATUS_ICON[svc.status];
        return (
          <Col xs={24} sm={12} lg={8} key={svc.name}>
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ fontSize: 24, color: cfg.color }}>{cfg.icon}</span>
                <div>
                  <Title level={5} style={{ margin: 0 }}>{svc.name}</Title>
                  <Text type="secondary">{svc.status === 'healthy' ? '正常' : svc.status === 'degraded' ? '降级' : '离线'}</Text>
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <Text type="secondary">可用性</Text>
                <Text strong style={{ marginLeft: 8 }}>{svc.uptime}</Text>
              </div>
            </Card>
          </Col>
        );
      })}
    </Row>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────

export default function Dashboard() {
  const { user } = useAuthStore();

  const role = user?.role ?? 'user';

  const items = useMemo(() => {
    const tabs = [
      {
        key: 'personal',
        label: (
          <span><DashboardOutlined /> 个人看板</span>
        ),
        children: <PersonalDashboard />,
      },
    ];

    if (role === 'org_admin' || role === 'team_admin') {
      tabs.push({
        key: 'org',
        label: (
          <span><TeamOutlined /> 组织看板</span>
        ),
        children: <OrganizationDashboard />,
      });
    }

    if (role === 'super_admin') {
      tabs.push({
        key: 'system',
        label: (
          <span><SettingOutlined /> 系统看板</span>
        ),
        children: <SystemDashboard />,
      });
    }

    return tabs;
  }, [role]);

  return (
    <div style={{ padding: '0 0 24px' }}>
      <Tabs defaultActiveKey="personal" items={items} />
    </div>
  );
}
