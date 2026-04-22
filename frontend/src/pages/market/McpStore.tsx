import { useCallback, useEffect, useState } from 'react';
import {
  Button,
  Card,
  Empty,
  Input,
  List,
  message,
  Modal,
  Pagination,
  Select,
  Spin,
  Tag,
  Typography,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { marketApi } from '@/api/market';
import { agentsApi } from '@/api/agents';
import type { McpServerItem, AgentInstance } from '@/types';

const { Text, Paragraph } = Typography;

const PAGE_SIZE = 12;

const TRANSPORT_COLORS: Record<string, string> = {
  stdio: 'blue',
  http: 'green',
  ws: 'purple',
};

export default function McpStore() {
  const [keyword, setKeyword] = useState('');
  const [mcps, setMcps] = useState<McpServerItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  // Configure modal
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [selectedMcp, setSelectedMcp] = useState<McpServerItem | null>(null);
  const [targetAgentId, setTargetAgentId] = useState<string | undefined>(undefined);
  const [configJson, setConfigJson] = useState('');
  const [agents, setAgents] = useState<AgentInstance[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [configuring, setConfiguring] = useState(false);

  const fetchMcps = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const res = await marketApi.getMcps({
        keyword: keyword || undefined,
        page: p,
        page_size: PAGE_SIZE,
      });
      setMcps(res.items);
      setTotal(res.total);
    } catch {
      message.error('加载 MCP Server 列表失败');
    } finally {
      setLoading(false);
    }
  }, [keyword]);

  useEffect(() => {
    fetchMcps(page);
  }, [page, fetchMcps]);

  const fetchAgents = async () => {
    setAgentsLoading(true);
    try {
      const res = await agentsApi.list({ page_size: 100 });
      setAgents(res.items);
    } catch {
      message.error('加载 Agent 列表失败');
    } finally {
      setAgentsLoading(false);
    }
  };

  const openConfigModal = (mcp: McpServerItem) => {
    setSelectedMcp(mcp);
    setTargetAgentId(undefined);
    setConfigJson(JSON.stringify(mcp.config_template ?? {}, null, 2));
    setConfigModalOpen(true);
    fetchAgents();
  };

  const handleConfigure = async () => {
    if (!selectedMcp || !targetAgentId) return;
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(configJson);
    } catch {
      message.error('配置 JSON 格式无效');
      return;
    }
    setConfiguring(true);
    try {
      await agentsApi.addMcp(targetAgentId, {
        name: selectedMcp.name,
        transport: selectedMcp.transport,
        ...parsed,
      } as any);
      message.success(`已将 ${selectedMcp.name} 配置到 Agent`);
      setConfigModalOpen(false);
    } catch {
      message.error('配置失败');
    } finally {
      setConfiguring(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginBottom: 24, color: 'var(--oh-text)' }}>
        MCP 商店
      </Typography.Title>

      <Input
        placeholder="搜索 MCP Server..."
        prefix={<SearchOutlined />}
        allowClear
        style={{ maxWidth: 400, marginBottom: 16 }}
        value={keyword}
        onChange={(e) => {
          setKeyword(e.target.value);
          setPage(1);
        }}
      />

      <Spin spinning={loading}>
        {!loading && mcps.length === 0 ? (
          <Empty description="暂无 MCP Server" />
        ) : (
          <>
            <List
              grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 4 }}
              dataSource={mcps}
              renderItem={(mcp) => (
                <List.Item>
                  <Card
                    style={{ height: '100%', backgroundColor: 'var(--oh-surface)', borderColor: 'var(--oh-border)' }}
                    actions={[
                      <Button type="primary" size="small" onClick={() => openConfigModal(mcp)}>
                        配置到 Agent
                      </Button>,
                    ]}
                  >
                    <Text strong style={{ color: 'var(--oh-text)', display: 'block', marginBottom: 4 }}>
                      {mcp.name}
                    </Text>
                    <Tag color={TRANSPORT_COLORS[mcp.transport] ?? 'default'} style={{ marginBottom: 8 }}>
                      {mcp.transport}
                    </Tag>
                    <Paragraph
                      type="secondary"
                      ellipsis={{ rows: 2 }}
                      style={{ color: 'var(--oh-text-secondary)', marginBottom: 8, minHeight: 44 }}
                    >
                      {mcp.description}
                    </Paragraph>
                    <pre
                      style={{
                        background: 'var(--oh-bg)',
                        border: '1px solid var(--oh-border)',
                        borderRadius: 4,
                        padding: '4px 8px',
                        fontSize: 11,
                        maxHeight: 80,
                        overflow: 'auto',
                        color: 'var(--oh-text-secondary)',
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-all',
                      }}
                    >
                      {JSON.stringify(mcp.config_template ?? {}, null, 2)}
                    </pre>
                  </Card>
                </List.Item>
              )}
            />
            {total > PAGE_SIZE && (
              <div style={{ display: 'flex', justifyContent: 'center', marginTop: 24 }}>
                <Pagination
                  current={page}
                  pageSize={PAGE_SIZE}
                  total={total}
                  showSizeChanger={false}
                  onChange={(p) => setPage(p)}
                />
              </div>
            )}
          </>
        )}
      </Spin>

      <Modal
        title={`配置 ${selectedMcp?.name ?? ''} 到 Agent`}
        open={configModalOpen}
        onOk={handleConfigure}
        onCancel={() => setConfigModalOpen(false)}
        confirmLoading={configuring}
        okText="确认配置"
        cancelText="取消"
        okButtonProps={{ disabled: !targetAgentId }}
        width={600}
      >
        <div style={{ marginBottom: 16 }}>
          <Text style={{ color: 'var(--oh-text)' }}>选择目标 Agent：</Text>
        </div>
        <Select
          showSearch
          placeholder="选择 Agent"
          loading={agentsLoading}
          style={{ width: '100%', marginBottom: 16 }}
          value={targetAgentId}
          onChange={setTargetAgentId}
          optionFilterProp="label"
          options={agents.map((a) => ({ value: a.id, label: a.name }))}
        />
        <div style={{ marginBottom: 8 }}>
          <Text style={{ color: 'var(--oh-text)' }}>配置 JSON：</Text>
        </div>
        <Input.TextArea
          value={configJson}
          onChange={(e) => setConfigJson(e.target.value)}
          rows={8}
          style={{
            fontFamily: 'monospace',
            fontSize: 13,
            backgroundColor: 'var(--oh-bg)',
            color: 'var(--oh-text)',
            borderColor: 'var(--oh-border)',
          }}
        />
      </Modal>
    </div>
  );
}
