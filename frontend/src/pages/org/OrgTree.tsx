import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  message,
  Modal,
  Row,
  Space,
  Spin,
  Table,
} from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import type { DataNode } from 'antd/es/tree';
import Tree from 'antd/es/tree';
import { orgApi } from '@/api/org';
import type { OrgNode, OrgDetail } from '@/types';

function buildTreeData(nodes: OrgNode[]): DataNode[] {
  return nodes.map((node) => ({
    key: node.id,
    title: (
      <Space>
        <span>{node.name}</span>
        <Badge count={node.member_count ?? 0} size="small" style={{ backgroundColor: 'var(--oh-primary)' }} />
      </Space>
    ),
    children: node.children ? buildTreeData(node.children) : undefined,
  }));
}

export default function OrgTree() {
  const [treeData, setTreeData] = useState<OrgNode[]>([]);
  const [treeLoading, setTreeLoading] = useState(false);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [detail, setDetail] = useState<OrgDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [form] = Form.useForm<{ name: string; description?: string }>();
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);

  const fetchTree = useCallback(async () => {
    setTreeLoading(true);
    try {
      const res = await orgApi.getTree();
      setTreeData(res.data ?? []);
      const keys: React.Key[] = [];
      const collect = (nodes: OrgNode[]) => {
        for (const n of nodes) {
          keys.push(n.id);
          if (n.children) collect(n.children);
        }
      };
      collect(res.data ?? []);
      setExpandedKeys(keys);
    } catch {
      message.error('加载组织树失败');
    } finally {
      setTreeLoading(false);
    }
  }, []);

  useEffect(() => { fetchTree(); }, [fetchTree]);

  const fetchDetail = useCallback(async (orgId: string) => {
    setDetailLoading(true);
    try {
      const res = await orgApi.get(orgId);
      setDetail(res.data);
    } catch {
      message.error('加载组织详情失败');
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleSelect = useCallback((keys: React.Key[]) => {
    if (keys.length > 0) {
      const key = String(keys[0]);
      setSelectedKey(key);
      fetchDetail(key);
    }
  }, [fetchDetail]);

  const handleCreate = useCallback(async () => {
    try {
      const values = await form.validateFields();
      if (!selectedKey) return;
      setCreateLoading(true);
      await orgApi.create({ name: values.name, parent_id: selectedKey });
      message.success('子组织创建成功');
      setCreateModalOpen(false);
      form.resetFields();
      fetchTree();
      fetchDetail(selectedKey);
    } catch {
      // validation or API error
    } finally {
      setCreateLoading(false);
    }
  }, [form, selectedKey, fetchTree, fetchDetail]);

  const childColumns = useMemo(() => [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '成员数',
      dataIndex: 'member_count',
      key: 'member_count',
      width: 100,
    },
  ], []);

  const parentName = useMemo(() => {
    if (!detail?.parent_id || !treeData.length) return '—';
    const find = (nodes: OrgNode[]): string | undefined => {
      for (const n of nodes) {
        if (n.id === detail.parent_id) return n.name;
        if (n.children) {
          const found = find(n.children);
          if (found) return found;
        }
      }
      return undefined;
    };
    return find(treeData) ?? '—';
  }, [detail, treeData]);

  const antTreeData = useMemo(() => buildTreeData(treeData), [treeData]);

  return (
    <div style={{ padding: 16 }}>
      <Row gutter={16}>
        {/* Left Sidebar — Tree */}
        <Col span={6}>
          <Card
            title="组织架构"
            size="small"
            extra={<Button type="text" size="small" icon={<ReloadOutlined />} onClick={fetchTree} />}
            styles={{ body: { padding: '8px 4px', maxHeight: 'calc(100vh - 200px)', overflow: 'auto' } }}
          >
            <Spin spinning={treeLoading}>
              {antTreeData.length > 0 ? (
                <Tree
                  showLine
                  defaultExpandAll
                  expandedKeys={expandedKeys}
                  onExpand={setExpandedKeys}
                  treeData={antTreeData}
                  onSelect={handleSelect}
                  selectedKeys={selectedKey ? [selectedKey] : []}
                  style={{ background: 'transparent' }}
                />
              ) : (
                <Empty description="暂无组织" />
              )}
            </Spin>
          </Card>
        </Col>

        {/* Right Content */}
        <Col span={18}>
          <Spin spinning={detailLoading}>
            {!selectedKey || !detail ? (
              <Card style={{ height: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Empty description="请在左侧选择一个组织" />
              </Card>
            ) : (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {/* Org Info */}
                <Card
                  title={detail.name}
                  size="small"
                  extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>创建子组织</Button>}
                  styles={{ body: { background: 'var(--oh-surface)' } }}
                >
                  <Descriptions column={2} size="small" bordered>
                    <Descriptions.Item label="名称">{detail.name}</Descriptions.Item>
                    <Descriptions.Item label="上级组织">{parentName}</Descriptions.Item>
                    <Descriptions.Item label="成员数">{detail.member_count}</Descriptions.Item>
                    <Descriptions.Item label="Agent 数">{detail.agent_count ?? 0}</Descriptions.Item>
                    <Descriptions.Item label="描述" span={2}>{detail.description ?? '—'}</Descriptions.Item>
                  </Descriptions>
                </Card>

                {/* Child Orgs */}
                {detail.children && detail.children.length > 0 && (
                  <Card title="下级组织" size="small" styles={{ body: { background: 'var(--oh-surface)' } }}>
                    <Table
                      dataSource={detail.children}
                      columns={childColumns}
                      rowKey="id"
                      size="small"
                      pagination={false}
                      onRow={(record) => ({
                        onClick: () => {
                          setSelectedKey(record.id);
                          fetchDetail(record.id);
                        },
                        style: { cursor: 'pointer' },
                      })}
                    />
                  </Card>
                )}
              </Space>
            )}
          </Spin>
        </Col>
      </Row>

      {/* Create Sub-org Modal */}
      <Modal
        title="创建子组织"
        open={createModalOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateModalOpen(false); form.resetFields(); }}
        confirmLoading={createLoading}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="组织名称" rules={[{ required: true, message: '请输入组织名称' }]}>
            <Input placeholder="请输入组织名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
