import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Badge,
  Button,
  Card,
  DatePicker,
  Input,
  message,
  Popconfirm,
  Select,
  Space,
  Table,
  Tooltip,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  DeleteOutlined,
  PoweroffOutlined,
} from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import { agentsApi } from '@/api/agents';
import type { AgentInstance, AgentStatus } from '@/types';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { RangePicker } = DatePicker;
const { Text, Link } = Typography;

// ─── Status badge config ──────────────────────────────────────────

const STATUS_BADGE: Record<AgentStatus, { status: 'success' | 'processing' | 'warning' | 'default' | 'error'; text: string }> = {
  ready: { status: 'success', text: 'Ready' },
  running: { status: 'processing', text: 'Running' },
  creating: { status: 'warning', text: 'Creating' },
  seeding: { status: 'warning', text: 'Seeding' },
  stopped: { status: 'default', text: 'Stopped' },
  failed: { status: 'error', text: 'Failed' },
  stopping: { status: 'warning', text: 'Stopping' },
};

const STATUS_OPTIONS: Array<{ value: AgentStatus | ''; label: string }> = [
  { value: '', label: 'All' },
  { value: 'creating', label: 'Creating' },
  { value: 'seeding', label: 'Seeding' },
  { value: 'ready', label: 'Ready' },
  { value: 'running', label: 'Running' },
  { value: 'stopped', label: 'Stopped' },
  { value: 'failed', label: 'Failed' },
];

// ─── Component ────────────────────────────────────────────────────

export default function AgentList() {
  const navigate = useNavigate();

  // Filters
  const [nameSearch, setNameSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<AgentStatus | ''>('');
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);

  // Table state
  const [data, setData] = useState<AgentInstance[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Batch selection
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [actionLoading, setActionLoading] = useState(false);

  // ─── Fetch data ─────────────────────────────────────────────────

  const fetchData = useCallback(async (p: number, ps: number) => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: ps };
      if (statusFilter) params.status = statusFilter;
      if (nameSearch.trim()) params.name = nameSearch.trim();
      if (dateRange) {
        params.created_after = dateRange[0].startOf('day').toISOString();
      }
      const res = await agentsApi.list(params);
      setData(res.items);
      setTotal(res.total);
    } catch {
      message.error('Failed to load agents');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, nameSearch, dateRange]);

  // Initial + filter changes
  useMemo(() => {
    setPage(1);
    fetchData(1, pageSize);
  }, [fetchData, pageSize]);

  const handleTableChange = useCallback((pagination: TablePaginationConfig) => {
    const p = pagination.current ?? 1;
    const ps = pagination.pageSize ?? 20;
    setPage(p);
    setPageSize(ps);
    fetchData(p, ps);
  }, [fetchData]);

  // Debounced name search
  const [searchTimer, setSearchTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const handleNameSearch = useCallback((value: string) => {
    setNameSearch(value);
    if (searchTimer) clearTimeout(searchTimer);
    const timer = setTimeout(() => {
      setPage(1);
      fetchData(1, pageSize);
    }, 400);
    setSearchTimer(timer);
  }, [searchTimer, fetchData, pageSize]);

  // Filter change handlers
  const handleStatusChange = useCallback((value: AgentStatus | '') => {
    setStatusFilter(value);
  }, []);

  const handleDateRangeChange = useCallback((dates: [Dayjs | null, Dayjs | null] | null) => {
    if (dates && dates[0] && dates[1]) {
      setDateRange([dates[0], dates[1]]);
    } else {
      setDateRange(null);
    }
  }, []);

  // ─── Actions ────────────────────────────────────────────────────

  const handleRestart = useCallback(async (id: string) => {
    try {
      await agentsApi.restart(id);
      message.success('Restart initiated');
      fetchData(page, pageSize);
    } catch {
      message.error('Restart failed');
    }
  }, [fetchData, page, pageSize]);

  const handleDestroy = useCallback(async (id: string) => {
    try {
      await agentsApi.destroy(id);
      message.success('Agent destroyed');
      fetchData(page, pageSize);
    } catch {
      message.error('Destroy failed');
    }
  }, [fetchData, page, pageSize]);

  const handleBatchRestart = useCallback(async () => {
    setActionLoading(true);
    try {
      await agentsApi.batchRestart({ ids: selectedRowKeys });
      message.success(`Restarting ${selectedRowKeys.length} agent(s)`);
      setSelectedRowKeys([]);
      fetchData(page, pageSize);
    } catch {
      message.error('Batch restart failed');
    } finally {
      setActionLoading(false);
    }
  }, [selectedRowKeys, fetchData, page, pageSize]);

  const handleBatchDestroy = useCallback(async () => {
    setActionLoading(true);
    try {
      await agentsApi.batchDestroy({ ids: selectedRowKeys });
      message.success(`${selectedRowKeys.length} agent(s) destroyed`);
      setSelectedRowKeys([]);
      fetchData(page, pageSize);
    } catch {
      message.error('Batch destroy failed');
    } finally {
      setActionLoading(false);
    }
  }, [selectedRowKeys, fetchData, page, pageSize]);

  // ─── Columns ────────────────────────────────────────────────────

  const columns: ColumnsType<AgentInstance> = useMemo(() => [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (name: string, record: AgentInstance) => (
        <Link
          onClick={() => navigate(`/agents/${record.id}`)}
          style={{ color: 'var(--oh-primary)', cursor: 'pointer' }}
        >
          {name}
        </Link>
      ),
    },
    {
      title: 'GUID',
      dataIndex: 'guid',
      key: 'guid',
      width: 180,
      render: (guid: string) => (
        <Tooltip title={guid}>
          <Text
            code
            style={{
              fontFamily: 'monospace',
              fontSize: 12,
              maxWidth: 160,
              display: 'inline-block',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              verticalAlign: 'middle',
            }}
          >
            {guid}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: AgentStatus) => {
        const badge = STATUS_BADGE[status] ?? { status: 'default' as const, text: status };
        return <Badge status={badge.status} text={badge.text} />;
      },
    },
    {
      title: 'Host Node',
      dataIndex: 'host_node',
      key: 'host_node',
      width: 150,
      render: (node: string | undefined) => (
        <Text type="secondary">{node || '-'}</Text>
      ),
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (ts: string) => dayjs(ts).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Last Active',
      dataIndex: 'last_active_at',
      key: 'last_active_at',
      width: 150,
      render: (ts: string | undefined) => (
        <Text type="secondary">{ts ? dayjs(ts).fromNow() : '-'}</Text>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 140,
      render: (_: unknown, record: AgentInstance) => (
        <Space size="small">
          <Tooltip title="Restart">
            <Popconfirm
              title="Restart this agent?"
              onConfirm={() => handleRestart(record.id)}
              okText="Restart"
              cancelText="Cancel"
            >
              <Button type="text" size="small" icon={<ReloadOutlined />} />
            </Popconfirm>
          </Tooltip>
          <Tooltip title="Destroy">
            <Popconfirm
              title="Destroy this agent? This cannot be undone."
              onConfirm={() => handleDestroy(record.id)}
              okText="Destroy"
              cancelText="Cancel"
              okButtonProps={{ danger: true }}
            >
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ], [navigate, handleRestart, handleDestroy]);

  // ─── Render ─────────────────────────────────────────────────────

  return (
    <div style={{ padding: 24 }}>
      {/* Filter bar */}
      <Card
        style={{
          marginBottom: 16,
          background: 'var(--oh-surface)',
          borderColor: 'var(--oh-border)',
        }}
        styles={{ body: { padding: '12px 16px' } }}
      >
        <Space wrap size="middle">
          <Input.Search
            placeholder="Search by name"
            allowClear
            style={{ width: 220 }}
            onSearch={handleNameSearch}
            onChange={(e) => { if (!e.target.value) handleNameSearch(''); }}
          />
          <Select
            value={statusFilter}
            onChange={handleStatusChange}
            style={{ width: 140 }}
            options={STATUS_OPTIONS}
          />
          <RangePicker
            onChange={handleDateRangeChange}
            placeholder={['Start date', 'End date']}
          />
        </Space>
      </Card>

      {/* Batch operations toolbar */}
      <Card
        style={{
          marginBottom: 16,
          background: 'var(--oh-surface)',
          borderColor: 'var(--oh-border)',
        }}
        styles={{ body: { padding: '8px 16px' } }}
      >
        <Space wrap>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/agents/new')}
            style={{ background: 'var(--oh-primary)', borderColor: 'var(--oh-primary)' }}
          >
            New Agent
          </Button>

          {selectedRowKeys.length > 0 && (
            <Text type="secondary" style={{ color: 'var(--oh-text-secondary)' }}>
              {selectedRowKeys.length} selected
            </Text>
          )}

          <Popconfirm
            title={`Restart ${selectedRowKeys.length} agent(s)?`}
            onConfirm={handleBatchRestart}
            okText="Restart"
            cancelText="Cancel"
            disabled={selectedRowKeys.length === 0}
          >
            <Button
              icon={<PoweroffOutlined />}
              disabled={selectedRowKeys.length === 0 || actionLoading}
              loading={actionLoading}
            >
              Batch Restart
            </Button>
          </Popconfirm>

          <Popconfirm
            title={`Destroy ${selectedRowKeys.length} agent(s)? This cannot be undone.`}
            onConfirm={handleBatchDestroy}
            okText="Destroy"
            cancelText="Cancel"
            disabled={selectedRowKeys.length === 0}
          >
            <Button
              danger
              icon={<DeleteOutlined />}
              disabled={selectedRowKeys.length === 0 || actionLoading}
              loading={actionLoading}
            >
              Batch Destroy
            </Button>
          </Popconfirm>
        </Space>
      </Card>

      {/* Table */}
      <Card
        style={{
          background: 'var(--oh-surface)',
          borderColor: 'var(--oh-border)',
        }}
      >
        <Table<AgentInstance>
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          locale={{ emptyText: 'No agents found' }}
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys as string[]),
          }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `Total ${t} agents`,
            pageSizeOptions: ['10', '20', '50'],
          }}
          onChange={handleTableChange}
          scroll={{ x: 1020 }}
          size="middle"
        />
      </Card>
    </div>
  );
}
