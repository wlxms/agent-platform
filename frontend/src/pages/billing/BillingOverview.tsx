import { useEffect, useMemo, useState } from 'react';
import { Card, Col, Empty, Progress, Row, Spin, Statistic, Table, Typography } from 'antd';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { LineChart, PieChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { billingApi } from '@/api/billing';
import type { BillingSummary } from '@/types';

echarts.use([LineChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

const { Title } = Typography;

function formatCost(v: number): string {
  return `¥${v.toFixed(2)}`;
}

function fmt(n: number): string {
  return n.toLocaleString();
}

const CARD_STYLE: React.CSSProperties = {
  background: 'var(--oh-surface)',
  borderColor: 'var(--oh-border)',
  borderRadius: 8,
};

export default function BillingOverview() {
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    billingApi
      .getSummary({ period: 'month' })
      .then((res) => {
        if (!cancelled) setSummary(res.data);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message ?? '加载失败');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const budgetPct = useMemo(() => {
    if (!summary?.budget || summary.budget <= 0) return 0;
    const spent = summary.budget - (summary.budget_remaining ?? 0);
    return Math.round((spent / summary.budget) * 100);
  }, [summary]);

  const lineOption = useMemo(() => {
    const days = summary?.daily_trend ?? [];
    return {
      tooltip: { trigger: 'axis' as const },
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
      xAxis: {
        type: 'category' as const,
        data: days.map((d) => d.date),
        axisLabel: { color: 'var(--oh-text-secondary)', fontSize: 11 },
      },
      yAxis: {
        type: 'value' as const,
        axisLabel: { formatter: '¥{value}', color: 'var(--oh-text-secondary)', fontSize: 11 },
      },
      series: [
        {
          type: 'line',
          data: days.map((d) => d.cost),
          smooth: true,
          areaStyle: { color: 'rgba(99,102,241,0.12)' },
          lineStyle: { color: 'var(--oh-primary)' },
          itemStyle: { color: 'var(--oh-primary)' },
        },
      ],
    };
  }, [summary]);

  const [pieView, setPieView] = useState<'agent' | 'model'>('agent');

  const pieOption = useMemo(() => {
    const src = pieView === 'agent' ? summary?.by_instance : summary?.by_model;
    if (!src?.length) return null;
    return {
      tooltip: { trigger: 'item' as const, formatter: '{b}: ¥{c} ({d}%)' },
      series: [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          label: { formatter: '{b}\n{d}%', fontSize: 11 },
          data: pieView === 'agent'
            ? summary!.by_instance!.map((d) => ({ name: d.agent_name, value: d.cost }))
            : summary!.by_model!.map((d) => ({ name: d.model, value: d.cost })),
        },
      ],
    };
  }, [summary, pieView]);

  const tableData = useMemo(() => {
    if (!summary?.by_instance?.length) return [];
    const sorted = [...summary.by_instance].sort((a, b) => b.cost - a.cost);
    return sorted.slice(0, 10).map((d, i) => ({
      key: d.agent_id ?? i,
      agent_name: d.agent_name,
      cost: d.cost,
      tokens: d.tokens,
      pct: summary.total_cost > 0 ? ((d.cost / summary.total_cost) * 100).toFixed(1) : '0.0',
    }));
  }, [summary]);

  const columns = [
    { title: 'Agent', dataIndex: 'agent_name', key: 'agent_name' },
    { title: '费用 (¥)', dataIndex: 'cost', key: 'cost', render: (v: number) => formatCost(v) },
    { title: 'Token 数', dataIndex: 'tokens', key: 'tokens', render: (v: number) => fmt(v) },
    { title: '占比', dataIndex: 'pct', key: 'pct', render: (v: string) => `${v}%` },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return <Empty description={error} />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Title level={4} style={{ color: 'var(--oh-text)' }}>账单概览</Title>

      {/* ── Stats Cards ── */}
      <Row gutter={16}>
        <Col xs={24} sm={8}>
          <Card style={CARD_STYLE}>
            <Statistic
              title="本月总费用"
              value={summary?.total_cost ?? 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: 'var(--oh-text)' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={CARD_STYLE}>
            <Statistic
              title="本月 Token 总量"
              value={summary?.total_tokens ?? 0}
              valueStyle={{ color: 'var(--oh-text)' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={CARD_STYLE}>
            <Statistic
              title="预算剩余"
              value={summary?.budget_remaining ?? 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: 'var(--oh-text)' }}
            />
            {(summary?.budget ?? 0) > 0 && (
              <Progress
                percent={budgetPct}
                strokeColor="var(--oh-primary)"
                size="small"
                style={{ marginTop: 8 }}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* ── Charts ── */}
      <Row gutter={16}>
        <Col xs={24} lg={14}>
          <Card title="费用趋势（近30天）" style={CARD_STYLE}>
            {summary?.daily_trend?.length ? (
              <ReactEChartsCore echarts={echarts} option={lineOption} style={{ height: 300 }} />
            ) : (
              <Empty description="暂无趋势数据" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card
            title="费用分布"
            style={CARD_STYLE}
            extra={
              <span style={{ fontSize: 12, color: 'var(--oh-text-secondary)' }}>
                <a
                  onClick={() => setPieView('agent')}
                  style={{ color: pieView === 'agent' ? 'var(--oh-primary)' : undefined, cursor: 'pointer', marginRight: 12 }}
                >
                  按Agent
                </a>
                <a
                  onClick={() => setPieView('model')}
                  style={{ color: pieView === 'model' ? 'var(--oh-primary)' : undefined, cursor: 'pointer' }}
                >
                  按模型
                </a>
              </span>
            }
          >
            {pieOption ? (
              <ReactEChartsCore echarts={echarts} option={pieOption} style={{ height: 300 }} />
            ) : (
              <Empty description="暂无分布数据" />
            )}
          </Card>
        </Col>
      </Row>

      {/* ── Top Agents Table ── */}
      <Card title="费用 Top 10 Agent" style={CARD_STYLE}>
        <Table
          dataSource={tableData}
          columns={columns}
          pagination={false}
          size="middle"
          locale={{ emptyText: '暂无数据' }}
        />
      </Card>
    </div>
  );
}
