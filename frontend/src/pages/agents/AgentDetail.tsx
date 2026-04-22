import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Tabs, Descriptions, Badge, Button, Input, Radio, Statistic,
  Popconfirm, Typography, Tree, Upload, Spin, message, Space, Tooltip,
  Row, Col,
} from 'antd';
import type { TabsProps } from 'antd';
import type { DataNode } from 'antd/es/tree';
import {
  ArrowLeftOutlined, CopyOutlined,
  StopOutlined, DeleteOutlined, UploadOutlined,
  DownloadOutlined, FolderOpenOutlined, FileOutlined,
  SaveOutlined, ReloadOutlined, ExpandOutlined,
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
import type {
  AgentInstance, AgentStatus, MonitorStats,
  MemoryTreeNode, PermissionMode,
} from '@/types';

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

const STATUS_COLOR: Record<AgentStatus, string> = {
  creating: 'processing',
  seeding: 'warning',
  ready: 'success',
  running: 'success',
  stopping: 'warning',
  stopped: 'default',
  failed: 'error',
};

const STATUS_LABEL: Record<AgentStatus, string> = {
  creating: '创建中',
  seeding: '初始化中',
  ready: '就绪',
  running: '运行中',
  stopping: '停止中',
  stopped: '已停止',
  failed: '失败',
};

const PERMISSION_OPTIONS: { value: PermissionMode; label: string; desc: string }[] = [
  { value: 'default', label: '默认', desc: '每项文件修改都需要用户确认' },
  { value: 'plan', label: '计划模式', desc: '仅规划不执行，需要用户审批后才会执行' },
  { value: 'acceptEdits', label: '接受编辑', desc: '自动接受所有文件编辑操作' },
  { value: 'bypassPermissions', label: '绕过权限', desc: '跳过所有权限检查，完全自主执行（危险）' },
];

const MAX_MONITOR_POINTS = 60;

function formatTimestamp(ts?: string): string {
  return ts ? dayjs(ts).format('YYYY-MM-DD HH:mm:ss') : '-';
}

// ─── Basic Info Panel ──────────────────────────────────────────────

function BasicInfoPanel({ agent }: { agent: AgentInstance }) {
  const copyGuid = useCallback(() => {
    navigator.clipboard.writeText(agent.guid);
    message.success('GUID 已复制');
  }, [agent.guid]);

  return (
    <Card
      style={{ borderRadius: 12, border: `1px solid var(--oh-border)` }}
      styles={{ body: { padding: 24 } }}
    >
      <Descriptions
        column={{ xs: 1, sm: 2, lg: 3 }}
        bordered
        size="middle"
        labelStyle={{ fontWeight: 500, color: 'var(--oh-text-secondary)', backgroundColor: 'var(--oh-surface)' }}
        contentStyle={{ backgroundColor: 'var(--oh-surface)' }}
      >
        <Descriptions.Item label="名称">{agent.name}</Descriptions.Item>
        <Descriptions.Item label="GUID">
          <Space>
            <Typography.Text code style={{ fontSize: 12 }}>{agent.guid}</Typography.Text>
            <Tooltip title="复制 GUID">
              <Button type="text" size="small" icon={<CopyOutlined />} onClick={copyGuid} />
            </Tooltip>
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="状态">
          <Badge
            status={STATUS_COLOR[agent.status] as any}
            text={<span style={{ color: 'var(--oh-text)' }}>{STATUS_LABEL[agent.status]}</span>}
          />
        </Descriptions.Item>
        <Descriptions.Item label="主机节点">{agent.host_node || '-'}</Descriptions.Item>
        <Descriptions.Item label="模型配置">
          {agent.model_config
            ? `${agent.model_config.provider} / ${agent.model_config.model}`
            : (agent.model || '-')}
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">{formatTimestamp(agent.created_at)}</Descriptions.Item>
        <Descriptions.Item label="更新时间">{formatTimestamp(agent.updated_at)}</Descriptions.Item>
        <Descriptions.Item label="最后活跃">{formatTimestamp(agent.last_active_at)}</Descriptions.Item>
      </Descriptions>
    </Card>
  );
}

// ─── Control Panel ─────────────────────────────────────────────────

function ControlPanel({ agent }: { agent: AgentInstance }) {
  const [promptValue, setPromptValue] = useState(agent.system_prompt || '');
  const [savingPrompt, setSavingPrompt] = useState(false);
  const [permissionSaving, setPermissionSaving] = useState(false);

  const savePrompt = useCallback(async () => {
    setSavingPrompt(true);
    try {
      await agentsApi.updateConfig(agent.id, { system_prompt: promptValue });
      message.success('系统提示词已保存');
    } catch {
      message.error('保存失败');
    } finally {
      setSavingPrompt(false);
    }
  }, [agent.id, promptValue]);

  const onPermissionChange = useCallback(async (mode: PermissionMode) => {
    setPermissionSaving(true);
    try {
      await agentsApi.updateConfig(agent.id, { permission_mode: mode });
      message.success('权限模式已更新');
    } catch {
      message.error('更新失败');
    } finally {
      setPermissionSaving(false);
    }
  }, [agent.id]);

  const restartAgent = useCallback(async () => {
    try {
      await agentsApi.restart(agent.id);
      message.success('重启指令已发送');
    } catch {
      message.error('重启失败');
    }
  }, [agent.id]);

  const stopAgent = useCallback(async () => {
    try {
      await agentsApi.stop(agent.id);
      message.success('停止指令已发送');
    } catch {
      message.error('停止失败');
    }
  }, [agent.id]);

  const destroyAgent = useCallback(async () => {
    try {
      await agentsApi.destroy(agent.id);
      message.success('实例已销毁');
    } catch {
      message.error('销毁失败');
    }
  }, [agent.id]);

  return (
    <>
      <Card
        title="系统提示词"
        style={{ borderRadius: 12, border: `1px solid var(--oh-border)`, marginBottom: 16 }}
        styles={{ body: { padding: 24 } }}
      >
        <Input.TextArea
          rows={4}
          value={promptValue}
          onChange={(e) => setPromptValue(e.target.value)}
          placeholder="输入 Agent 系统提示词..."
          style={{ marginBottom: 12 }}
        />
        <Button
          type="primary"
          icon={<SaveOutlined />}
          loading={savingPrompt}
          onClick={savePrompt}
        >
          保存提示词
        </Button>
      </Card>

      <Card
        title="权限模式"
        style={{ borderRadius: 12, border: `1px solid var(--oh-border)`, marginBottom: 16 }}
        styles={{ body: { padding: 24 } }}
      >
        <Radio.Group
          value={agent.permission_mode || 'default'}
          onChange={(e) => onPermissionChange(e.target.value)}
          optionType="button"
          buttonStyle="solid"
          disabled={permissionSaving}
        >
          {PERMISSION_OPTIONS.map((opt) => (
            <Tooltip key={opt.value} title={opt.desc}>
              <Radio.Button value={opt.value}>{opt.label}</Radio.Button>
            </Tooltip>
          ))}
        </Radio.Group>
      </Card>

      <Card
        title="操作"
        style={{ borderRadius: 12, border: `1px solid var(--oh-border)` }}
        styles={{ body: { padding: 24 } }}
      >
        <Space>
          <Popconfirm
            title="确认重启"
            description="该操作将重启此 Agent 实例"
            onConfirm={restartAgent}
            okText="确认"
            cancelText="取消"
          >
            <Button icon={<ReloadOutlined />}>重启</Button>
          </Popconfirm>
          <Popconfirm
            title="确认停止"
            description="该操作将停止此 Agent 实例"
            onConfirm={stopAgent}
            okText="确认"
            cancelText="取消"
          >
            <Button icon={<StopOutlined />}>停止</Button>
          </Popconfirm>
          <Popconfirm
            title="⚠️ 确认销毁"
            description="此操作不可逆！该 Agent 实例及其所有数据将被永久删除"
            onConfirm={destroyAgent}
            okText="确认销毁"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button danger icon={<DeleteOutlined />}>销毁</Button>
          </Popconfirm>
        </Space>
      </Card>
    </>
  );
}

// ─── Memory Sync Panel ─────────────────────────────────────────────

function MemorySyncPanel({ agentId }: { agentId: string }) {
  const [treeData, setTreeData] = useState<DataNode[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTree = useCallback(async () => {
    setLoading(true);
    try {
      const res = await agentsApi.getMemoryTree(agentId);
      const convertNode = (node: MemoryTreeNode): DataNode => ({
        key: node.path,
        title: node.name || node.path.split('/').pop() || node.path,
        icon: node.type === 'directory' ? <FolderOpenOutlined /> : <FileOutlined />,
        isLeaf: node.type === 'file',
        children: node.children?.map(convertNode),
      });
      setTreeData((res.data.tree as MemoryTreeNode[]).map(convertNode));
    } catch {
      setTreeData([]);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    fetchTree();
  }, [fetchTree]);

  const handleDownload = useCallback(async (path: string) => {
    try {
      const res = await agentsApi.downloadMemory(agentId, path);
      const url = URL.createObjectURL(new Blob([res as any]));
      const a = document.createElement('a');
      a.href = url;
      a.download = path.split('/').pop() || 'download';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error('下载失败');
    }
  }, [agentId]);

  const handleView = useCallback(async (path: string) => {
    try {
      const res = await agentsApi.downloadMemory(agentId, path);
      const text = await (res as any).text();
      message.info(`文件内容预览: ${path.substring(path.lastIndexOf('/') + 1)}\n${text.substring(0, 200)}${text.length > 200 ? '...' : ''}`);
    } catch {
      message.error('读取文件失败');
    }
  }, [agentId]);

  const handleUpload = useCallback(async (info: any) => {
    const { file, onSuccess, onError } = info;
    const formData = new FormData();
    formData.append('file', file);
    try {
      await agentsApi.uploadMemory(agentId, formData);
      message.success(`已上传: ${file.name}`);
      onSuccess?.();
      fetchTree();
    } catch {
      message.error(`上传失败: ${file.name}`);
      onError?.();
    }
  }, [agentId, fetchTree]);

  return (
    <Card
      title="记忆文件"
      style={{ borderRadius: 12, border: `1px solid var(--oh-border)` }}
      styles={{ body: { padding: 24 } }}
      extra={
        <Upload.Dragger
          customRequest={handleUpload as any}
          showUploadList={false}
          multiple
        >
          <Button icon={<UploadOutlined />}>上传文件</Button>
        </Upload.Dragger>
      }
    >
      <Spin spinning={loading}>
        {treeData.length === 0 && !loading ? (
          <Typography.Text type="secondary">暂无记忆文件</Typography.Text>
        ) : (
          <Tree
            showIcon
            treeData={treeData}
            defaultExpandAll
            titleRender={(node: any) => (
              <Space>
                <span>{node.title as string}</span>
                {!node.isLeaf ? null : (
                  <>
                    <Tooltip title="查看">
                      <Button
                        type="text"
                        size="small"
                        icon={<ExpandOutlined />}
                        onClick={(e) => { e.stopPropagation(); handleView(node.key); }}
                      />
                    </Tooltip>
                    <Tooltip title="下载">
                      <Button
                        type="text"
                        size="small"
                        icon={<DownloadOutlined />}
                        onClick={(e) => { e.stopPropagation(); handleDownload(node.key); }}
                      />
                    </Tooltip>
                  </>
                )}
              </Space>
            )}
          />
        )}
      </Spin>
    </Card>
  );
}

// ─── Monitor Panel ─────────────────────────────────────────────────

function MonitorPanel({ agentId }: { agentId: string }) {
  const [stats, setStats] = useState<MonitorStats | null>(null);
  const [cpuHistory, setCpuHistory] = useState<number[]>([]);
  const [memHistory, setMemHistory] = useState<number[]>([]);
  const [timeLabels, setTimeLabels] = useState<string[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const addDataPoint = useCallback((s: MonitorStats) => {
    const ts = dayjs().format('HH:mm:ss');
    setTimeLabels((prev) => {
      const next = [...prev, ts];
      return next.length > MAX_MONITOR_POINTS ? next.slice(-MAX_MONITOR_POINTS) : next;
    });
    setCpuHistory((prev) => {
      const next = [...prev, s.cpu_percent];
      return next.length > MAX_MONITOR_POINTS ? next.slice(-MAX_MONITOR_POINTS) : next;
    });
    setMemHistory((prev) => {
      const next = [...prev, s.memory_mb];
      return next.length > MAX_MONITOR_POINTS ? next.slice(-MAX_MONITOR_POINTS) : next;
    });
    setStats(s);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const fetchMonitor = async () => {
      try {
        const res = await agentsApi.getMonitor(agentId);
        if (!cancelled) addDataPoint(res.data);
      } catch {
        // ignore single poll failure
      }
    };
    fetchMonitor();
    intervalRef.current = setInterval(fetchMonitor, 5000);
    return () => {
      cancelled = true;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [agentId, addDataPoint]);

  const chartOption = useMemo(() => ({
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['CPU (%)', 'Memory (MB)'], textStyle: { color: 'var(--oh-text)' } },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category' as const, data: timeLabels, boundaryGap: false },
    yAxis: { type: 'value' as const },
    series: [
      {
        name: 'CPU (%)',
        type: 'line',
        data: cpuHistory,
        smooth: true,
        itemStyle: { color: 'var(--oh-primary)' },
        areaStyle: { color: 'var(--oh-primary)' },
      },
      {
        name: 'Memory (MB)',
        type: 'line',
        data: memHistory,
        smooth: true,
        itemStyle: { color: '#f59e0b' },
        areaStyle: { color: '#f59e0b' },
      },
    ],
  }), [timeLabels, cpuHistory, memHistory]);

  return (
    <>
      <Card
        title="实时监控"
        style={{ borderRadius: 12, border: `1px solid var(--oh-border)`, marginBottom: 16 }}
        styles={{ body: { padding: 24 } }}
      >
        <ReactEChartsCore
          echarts={echarts}
          option={chartOption}
          style={{ height: 300 }}
          notMerge
          lazyUpdate
        />
      </Card>
      <Card
        style={{ borderRadius: 12, border: `1px solid var(--oh-border)` }}
        styles={{ body: { padding: 24 } }}
      >
        <Row gutter={24}>
          <Col span={8}>
            <Statistic
              title="CPU 使用率"
              value={stats?.cpu_percent ?? 0}
              suffix="%"
              precision={1}
              valueStyle={{ color: 'var(--oh-primary)' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="内存使用"
              value={stats?.memory_mb ?? 0}
              suffix=" MB"
              precision={1}
              valueStyle={{ color: '#f59e0b' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="总 Token 消耗"
              value={stats?.total_tokens ?? 0}
              valueStyle={{ color: 'var(--oh-text)' }}
            />
          </Col>
        </Row>
      </Card>
    </>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────

export default function AgentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [agent, setAgent] = useState<AgentInstance | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const fetchAgent = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setNotFound(false);
    try {
      const res = await agentsApi.get(id);
      setAgent(res.data);
    } catch (err: any) {
      if (err?.response?.status === 404 || err?.response?.data?.code === 'NOT_FOUND') {
        setNotFound(true);
      } else {
        message.error('加载 Agent 详情失败');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAgent();
  }, [fetchAgent]);

  if (!id || notFound) {
    return (
      <Card style={{ borderRadius: 12 }}>
        <Typography.Title level={4}>Agent 未找到</Typography.Title>
        <Typography.Text type="secondary">
          请求的 Agent 实例不存在或已被销毁。
        </Typography.Text>
        <Button style={{ marginTop: 16 }} onClick={() => navigate('/agents')}>
          返回列表
        </Button>
      </Card>
    );
  }

  const tabItems: TabsProps['items'] = [
    {
      key: 'info',
      label: '基本信息',
      children: agent ? <BasicInfoPanel agent={agent} /> : null,
    },
    {
      key: 'control',
      label: '控制面板',
      children: agent ? <ControlPanel agent={agent} /> : null,
    },
    {
      key: 'memory',
      label: '记忆同步',
      children: <MemorySyncPanel agentId={id} />,
    },
    {
      key: 'monitor',
      label: '监控',
      children: <MonitorPanel agentId={id} />,
    },
  ];

  return (
    <div>
      <Button
        type="text"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/agents')}
        style={{ marginBottom: 16, color: 'var(--oh-text-secondary)' }}
      >
        返回列表
      </Button>
      <Spin spinning={loading}>
        <Tabs defaultActiveKey="info" items={tabItems} size="large" />
      </Spin>
    </div>
  );
}
