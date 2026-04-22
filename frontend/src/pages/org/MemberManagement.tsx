import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import { PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import { orgApi } from '@/api/org';
import type { OrgNode, OrgMember, UserRole } from '@/types';

const { Title } = Typography;

const ROLE_TAG_COLOR: Record<UserRole, string> = {
  super_admin: 'red',
  org_admin: 'orange',
  team_admin: 'blue',
  user: 'default',
};

const ROLE_LABEL: Record<UserRole, string> = {
  super_admin: '超级管理员',
  org_admin: '组织管理员',
  team_admin: '团队管理员',
  user: '普通用户',
};

const ROLE_OPTIONS: Array<{ value: UserRole | ''; label: string }> = [
  { value: '', label: '全部' },
  { value: 'super_admin', label: '超级管理员' },
  { value: 'org_admin', label: '组织管理员' },
  { value: 'team_admin', label: '团队管理员' },
  { value: 'user', label: '普通用户' },
];

function flattenOrgTree(nodes: OrgNode[]): Array<{ id: string; name: string }> {
  const result: Array<{ id: string; name: string }> = [];
  const walk = (items: OrgNode[]) => {
    for (const n of items) {
      result.push({ id: n.id, name: n.name });
      if (n.children) walk(n.children);
    }
  };
  walk(nodes);
  return result;
}

export default function MemberManagement() {
  // Filters
  const [orgFilter, setOrgFilter] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<UserRole | ''>('');
  const [searchText, setSearchText] = useState('');

  // Table
  const [members, setMembers] = useState<OrgMember[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Org tree for selects
  const [orgTree, setOrgTree] = useState<OrgNode[]>([]);
  const [orgOptions, setOrgOptions] = useState<Array<{ id: string; name: string }>>([]);

  // Modal
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [addLoading, setAddLoading] = useState(false);
  const [form] = Form.useForm<{ user_id: string; role: UserRole; org_id: string }>();

  // Action loading keys
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});

  // ─── Fetch org tree ─────────────────────────────────────────────

  const fetchOrgTree = useCallback(async () => {
    try {
      const res = await orgApi.getTree();
      const tree = res.data ?? [];
      setOrgTree(tree);
      setOrgOptions(flattenOrgTree(tree));
      // Auto-select first org if none selected
      if (!orgFilter && tree.length > 0) {
        setOrgFilter(tree[0]?.id ?? '');
      }
    } catch {
      message.error('加载组织列表失败');
    }
  }, []);

  useEffect(() => { fetchOrgTree(); }, [fetchOrgTree]);

  // ─── Fetch members ──────────────────────────────────────────────

  const fetchMembers = useCallback(async (p: number, ps: number) => {
    if (!orgFilter) {
      setMembers([]);
      setTotal(0);
      return;
    }
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page: p, page_size: ps };
      if (roleFilter) params.role = roleFilter;
      if (searchText.trim()) params.username = searchText.trim();
      const res = await orgApi.getMembers(orgFilter, params);
      setMembers(res.items);
      setTotal(res.total);
    } catch {
      message.error('加载成员列表失败');
    } finally {
      setLoading(false);
    }
  }, [orgFilter, roleFilter, searchText]);

  useEffect(() => {
    setPage(1);
    fetchMembers(1, pageSize);
  }, [fetchMembers, pageSize]);

  const handleTableChange = useCallback((pagination: TablePaginationConfig) => {
    const p = pagination.current ?? 1;
    const ps = pagination.pageSize ?? 20;
    setPage(p);
    setPageSize(ps);
    fetchMembers(p, ps);
  }, [fetchMembers]);

  // ─── Actions ────────────────────────────────────────────────────

  const handleChangeRole = useCallback(async (userId: string, role: UserRole) => {
    if (!orgFilter) return;
    setActionLoading((prev) => ({ ...prev, [userId]: true }));
    try {
      await orgApi.updateMemberRole(orgFilter, userId, { role });
      message.success('角色已更新');
      fetchMembers(page, pageSize);
    } catch {
      message.error('更新角色失败');
    } finally {
      setActionLoading((prev) => ({ ...prev, [userId]: false }));
    }
  }, [orgFilter, page, pageSize, fetchMembers]);

  const handleRemove = useCallback(async (userId: string) => {
    if (!orgFilter) return;
    setActionLoading((prev) => ({ ...prev, [userId]: true }));
    try {
      await orgApi.removeMember(orgFilter, userId);
      message.success('成员已移除');
      fetchMembers(page, pageSize);
    } catch {
      message.error('移除成员失败');
    } finally {
      setActionLoading((prev) => ({ ...prev, [userId]: false }));
    }
  }, [orgFilter, page, pageSize, fetchMembers]);

  const handleAdd = useCallback(async () => {
    try {
      const values = await form.validateFields();
      if (!values.org_id) {
        message.warning('请选择组织');
        return;
      }
      setAddLoading(true);
      await orgApi.addMember(values.org_id, { user_id: values.user_id, role: values.role });
      message.success('成员添加成功');
      setAddModalOpen(false);
      form.resetFields();
      // Refresh if viewing the target org
      if (values.org_id === orgFilter) {
        fetchMembers(page, pageSize);
      }
    } catch {
      // validation or API error
    } finally {
      setAddLoading(false);
    }
  }, [form, orgFilter, page, pageSize, fetchMembers]);

  // ─── Get org name helper ────────────────────────────────────────

  const getOrgName = useCallback((orgId: string) => {
    const find = (nodes: OrgNode[]): string | undefined => {
      for (const n of nodes) {
        if (n.id === orgId) return n.name;
        if (n.children) {
          const found = find(n.children);
          if (found) return found;
        }
      }
      return undefined;
    };
    return find(orgTree) ?? orgId;
  }, [orgTree]);

  // ─── Columns ────────────────────────────────────────────────────

  const columns: ColumnsType<OrgMember> = useMemo(() => [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 140,
      render: (role: UserRole) => (
        <Tag color={ROLE_TAG_COLOR[role]}>{ROLE_LABEL[role]}</Tag>
      ),
    },
    {
      title: '组织',
      dataIndex: 'org_id',
      key: 'org_id',
      render: (orgId: string) => getOrgName(orgId),
    },
    {
      title: '加入时间',
      dataIndex: 'joined_at',
      key: 'joined_at',
      width: 180,
      render: (val: string) => val ? new Date(val).toLocaleString('zh-CN') : '—',
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Select
            size="small"
            value={record.role}
            style={{ width: 120 }}
            onChange={(val) => handleChangeRole(record.user_id, val)}
            loading={actionLoading[record.user_id]}
            options={ROLE_OPTIONS.filter((o) => o.value !== '').map((o) => ({ value: o.value, label: o.label }))}
          />
          <Popconfirm
            title="确定移除该成员？"
            onConfirm={() => handleRemove(record.user_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button size="small" danger loading={actionLoading[record.user_id]}>移除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ], [getOrgName, handleChangeRole, handleRemove, actionLoading]);

  return (
    <div style={{ padding: 16 }}>
      <Card
        title={<Title level={4} style={{ margin: 0 }}>成员管理</Title>}
        size="small"
        styles={{ body: { background: 'var(--oh-surface)' } }}
      >
        {/* Filter bar */}
        <Space wrap style={{ marginBottom: 16 }}>
          <Select
            placeholder="选择组织"
            style={{ width: 220 }}
            value={orgFilter || undefined}
            onChange={(val) => setOrgFilter(val)}
            options={orgOptions.map((o) => ({ value: o.id, label: o.name }))}
            allowClear
          />
          <Select
            placeholder="角色筛选"
            style={{ width: 140 }}
            value={roleFilter || undefined}
            onChange={(val) => setRoleFilter(val)}
            options={ROLE_OPTIONS}
          />
          <Input.Search
            placeholder="搜索用户名"
            allowClear
            prefix={<SearchOutlined />}
            style={{ width: 220 }}
            onSearch={(val) => setSearchText(val)}
          />
          <Button icon={<ReloadOutlined />} onClick={() => fetchMembers(page, pageSize)}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)}>添加成员</Button>
        </Space>

        {/* Table */}
        <Table<OrgMember>
          dataSource={members}
          columns={columns}
          rowKey="user_id"
          loading={loading}
          size="small"
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
          }}
          onChange={handleTableChange}
          locale={{ emptyText: orgFilter ? '暂无成员' : '请先选择组织' }}
        />
      </Card>

      {/* Add Member Modal */}
      <Modal
        title="添加成员"
        open={addModalOpen}
        onOk={handleAdd}
        onCancel={() => { setAddModalOpen(false); form.resetFields(); }}
        confirmLoading={addLoading}
        okText="添加"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="user_id" label="用户 ID" rules={[{ required: true, message: '请输入用户 ID' }]}>
            <Input placeholder="请输入用户 ID" />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true, message: '请选择角色' }]} initialValue="user">
            <Select options={ROLE_OPTIONS.filter((o) => o.value !== '').map((o) => ({ value: o.value, label: o.label }))} />
          </Form.Item>
          <Form.Item name="org_id" label="组织" rules={[{ required: true, message: '请选择组织' }]} initialValue={orgFilter}>
            <Select
              showSearch
              optionFilterProp="label"
              options={orgOptions.map((o) => ({ value: o.id, label: o.name }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
