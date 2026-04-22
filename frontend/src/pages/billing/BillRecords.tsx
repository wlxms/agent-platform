import { useCallback, useEffect, useState } from 'react';
import { Button, Card, DatePicker, Empty, Select, Space, Table, Tag, Typography, message } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { billingApi } from '@/api/billing';
import { agentsApi } from '@/api/agents';
import type { BillingRecord } from '@/types';

const { RangePicker } = DatePicker;
const { Title } = Typography;

const TYPE_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'api_call', label: 'API 调用' },
  { value: 'storage', label: '存储' },
  { value: 'bandwidth', label: '带宽' },
];

const TYPE_TAG: Record<string, { color: string; label: string }> = {
  api_call: { color: 'blue', label: 'API 调用' },
  storage: { color: 'green', label: '存储' },
  bandwidth: { color: 'orange', label: '带宽' },
};

const CARD_STYLE: React.CSSProperties = {
  background: 'var(--oh-surface)',
  borderColor: 'var(--oh-border)',
  borderRadius: 8,
};

export default function BillRecords() {
  const [records, setRecords] = useState<BillingRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Filters
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);
  const [agentId, setAgentId] = useState<string | undefined>();
  const [recordType, setRecordType] = useState<string>('');

  // Agent list for select
  const [agentOptions, setAgentOptions] = useState<Array<{ value: string; label: string }>>([]);

  useEffect(() => {
    agentsApi.list({ page: 1, page_size: 200 }).then((res) => {
      setAgentOptions(res.items.map((a) => ({ value: a.id, label: a.name })));
    }).catch(() => {});
  }, []);

  const fetchRecords = useCallback(() => {
    setLoading(true);
    billingApi
      .getRecords({
        page,
        page_size: pageSize,
        agent_id: agentId || undefined,
        created_after: dateRange?.[0]?.toISOString(),
        created_before: dateRange?.[1]?.toISOString(),
      })
      .then((res) => {
        setRecords(res.items);
        setTotal(res.total);
      })
      .catch(() => message.error('加载账单记录失败'))
      .finally(() => setLoading(false));
  }, [page, pageSize, agentId, dateRange]);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await billingApi.exportCsv({
        agent_id: agentId || undefined,
        created_after: dateRange?.[0]?.toISOString(),
        created_before: dateRange?.[1]?.toISOString(),
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `billing-records-${dayjs().format('YYYY-MM-DD')}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      message.error('导出失败');
    } finally {
      setExporting(false);
    }
  };

  const handleTableChange = (pagination: TablePaginationConfig) => {
    if (pagination.current && pagination.current !== page) {
      setPage(pagination.current);
    }
  };

  const columns: ColumnsType<BillingRecord> = [
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      width: 180,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Agent',
      dataIndex: 'agent_name',
      key: 'agent_name',
      width: 140,
      render: (v: string) => v || '-',
    },
    {
      title: '类型',
      dataIndex: 'model',
      key: 'type',
      width: 100,
      render: (v: string) => {
        const info = TYPE_TAG[v];
        return info ? <Tag color={info.color}>{info.label}</Tag> : <Tag>{v || '-'}</Tag>;
      },
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      ellipsis: true,
    },
    {
      title: 'Token 数',
      key: 'tokens',
      width: 120,
      render: (_, r) => (r.total_tokens ?? 0).toLocaleString(),
    },
    {
      title: '费用 (¥)',
      dataIndex: 'cost',
      key: 'cost',
      width: 110,
      render: (v: number) => `¥${(v ?? 0).toFixed(2)}`,
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Title level={4} style={{ color: 'var(--oh-text)' }}>账单记录</Title>

      <Card style={CARD_STYLE}>
        {/* ── Filter Bar ── */}
        <Space wrap style={{ marginBottom: 16 }}>
          <RangePicker
            onChange={(dates) => {
              setDateRange(dates as [Dayjs | null, Dayjs | null] | null);
              setPage(1);
            }}
          />
          <Select
            placeholder="筛选 Agent"
            allowClear
            style={{ width: 180 }}
            options={agentOptions}
            value={agentId || undefined}
            onChange={(v) => { setAgentId(v || undefined); setPage(1); }}
          />
          <Select
            style={{ width: 130 }}
            options={TYPE_OPTIONS}
            value={recordType}
            onChange={(v) => { setRecordType(v); setPage(1); }}
          />
          <Button
            icon={<DownloadOutlined />}
            loading={exporting}
            onClick={handleExport}
          >
            导出 CSV
          </Button>
        </Space>

        {/* ── Records Table ── */}
        <Table<BillingRecord>
          dataSource={records}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="middle"
          locale={{ emptyText: <Empty description="暂无记录" /> }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 条`,
          }}
          onChange={handleTableChange}
        />
      </Card>
    </div>
  );
}
