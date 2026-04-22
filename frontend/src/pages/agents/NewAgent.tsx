import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card, Form, Input, Select, Radio, Slider, InputNumber, Button,
  Divider, Typography, message, Collapse, Space, Alert,
} from 'antd';
import { agentsApi } from '@/api/agents';
import { marketApi } from '@/api/market';
import { tasksApi } from '@/api/tasks';
import type { Template, CreateAgentRequest, TaskStatus } from '@/types';

const { Title, Text } = Typography;
const { TextArea } = Input;

const PROVIDER_OPTIONS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'ollama', label: 'Ollama' },
  { value: 'azure', label: 'Azure OpenAI' },
  { value: 'other', label: '其他' },
];

const PERMISSION_OPTIONS = [
  { value: 'default', label: 'default' },
  { value: 'plan', label: 'plan' },
  { value: 'acceptEdits', label: 'acceptEdits' },
  { value: 'bypassPermissions', label: 'bypassPermissions' },
];

const RESOURCE_SPECS: Record<string, { cpu: string; ram: string; label: string }> = {
  lightweight: { cpu: '1 CPU', ram: '2 GB RAM', label: '轻量' },
  standard: { cpu: '2 CPU', ram: '4 GB RAM', label: '标准' },
  high_performance: { cpu: '4 CPU', ram: '8 GB RAM', label: '高性能' },
};

const RESOURCE_RADIO_OPTIONS = [
  { value: 'lightweight', label: '轻量 (1 CPU / 2 GB)' },
  { value: 'standard', label: '标准 (2 CPU / 4 GB)' },
  { value: 'high_performance', label: '高性能 (4 CPU / 8 GB)' },
];

export default function NewAgent() {
  const navigate = useNavigate();
  const [form] = Form.useForm<CreateAgentRequest>();
  const [templateMode, setTemplateMode] = useState<'template' | 'custom'>('custom');
  const [templates, setTemplates] = useState<Template[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);

  const loadTemplates = useCallback(async () => {
    setTemplatesLoading(true);
    try {
      const res = await marketApi.getTemplates({ page_size: 100 });
      setTemplates(res.items);
    } catch {
      message.error('加载模板列表失败');
    } finally {
      setTemplatesLoading(false);
    }
  }, []);

  useEffect(() => {
    if (templateMode === 'template' && templates.length === 0) {
      void loadTemplates();
    }
  }, [templateMode, templates.length, loadTemplates]);

  const handleTemplateSelect = (templateId: string) => {
    const tpl = templates.find((t) => t.id === templateId);
    if (!tpl) return;
    form.setFieldsValue({
      name: tpl.name,
      template_id: tpl.id,
      resource_spec: undefined,
      config: {
        system_prompt: '',
        permission_mode: 'default',
      },
    });
  };

  const handleSubmit = async (values: CreateAgentRequest) => {
    setSubmitting(true);
    try {
      const res = await agentsApi.create(values);
      const newTaskId = res.data.task_id;
      setTaskId(newTaskId);
      message.success('Agent 创建任务已提交');

      void pollTaskStatus(newTaskId);
    } catch {
      message.error('创建失败，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  const pollTaskStatus = async (id: string) => {
    let attempts = 0;
    const maxAttempts = 30;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const res = await tasksApi.getStatus(id);
        setTaskStatus(res.data.status);
        if (res.data.status === 'completed' || res.data.status === 'failed' || attempts >= maxAttempts) {
          clearInterval(interval);
          if (res.data.status === 'completed') {
            message.success('Agent 创建成功');
            navigate('/agents');
          } else if (res.data.status === 'failed') {
            message.error(res.data.error ?? 'Agent 创建失败');
          }
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
  };

  const handleCancel = () => {
    navigate('/agents');
  };

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: '24px 0' }}>
      <Card
        title={<Title level={4} style={{ margin: 0 }}>创建 Agent 实例</Title>}
        style={{
          borderRadius: 12,
          border: `1px solid var(--oh-border)`,
          backgroundColor: 'var(--oh-surface)',
        }}
      >
        {taskId && taskStatus && (
          <Alert
            style={{ marginBottom: 16 }}
            type={
              taskStatus === 'completed' ? 'success' :
              taskStatus === 'failed' ? 'error' : 'info'
            }
            message={`任务状态: ${taskStatus}`}
            showIcon
          />
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            model: {
              provider: 'openai',
              temperature: 0.7,
              max_tokens: 4096,
            },
            resource_spec: 'standard',
            config: {
              permission_mode: 'default',
            },
          }}
        >
          {/* ── Template Selection ── */}
          <Form.Item label="创建方式">
            <Radio.Group
              value={templateMode}
              onChange={(e) => setTemplateMode(e.target.value)}
            >
              <Radio value="template">从模板创建</Radio>
              <Radio value="custom">自定义配置</Radio>
            </Radio.Group>
          </Form.Item>

          {templateMode === 'template' && (
            <Form.Item
              name="template_id"
              label="选择模板"
              rules={[{ required: true, message: '请选择模板' }]}
            >
              <Select
                placeholder="请选择模板"
                loading={templatesLoading}
                showSearch
                optionFilterProp="label"
                options={templates.map((t) => ({
                  value: t.id,
                  label: t.name,
                }))}
                onChange={handleTemplateSelect}
              />
            </Form.Item>
          )}

          <Divider />

          {/* ── Basic Info ── */}
          <Form.Item
            name="name"
            label="名称"
            tooltip="Agent 实例的唯一名称"
            rules={[
              { required: true, message: '请输入 Agent 名称' },
              { max: 64, message: '名称不能超过 64 个字符' },
            ]}
          >
            <Input placeholder="输入 Agent 名称" maxLength={64} showCount />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
            tooltip="可选的 Agent 描述信息"
            rules={[{ max: 500, message: '描述不能超过 500 个字符' }]}
          >
            <TextArea placeholder="输入描述（可选）" rows={3} maxLength={500} showCount />
          </Form.Item>

          <Divider />

          {/* ── Model Configuration ── */}
          <Title level={5} style={{ color: 'var(--oh-text)', marginBottom: 16 }}>模型配置</Title>

          <Form.Item
            name={['model', 'provider']}
            label="Provider"
            rules={[{ required: true, message: '请选择 Provider' }]}
          >
            <Select options={PROVIDER_OPTIONS} placeholder="选择 Provider" />
          </Form.Item>

          <Form.Item
            name={['model', 'model']}
            label="模型"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="e.g. gpt-4, claude-3-opus, llama3" />
          </Form.Item>

          <Form.Item
            name={['model', 'api_base']}
            label="API Base URL"
            tooltip="可选，留空使用默认地址"
          >
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item
            name={['model', 'api_key']}
            label="API Key"
            tooltip="可选，敏感信息将被加密存储"
          >
            <Input.Password placeholder="sk-..." />
          </Form.Item>

          <Form.Item
            name={['model', 'temperature']}
            label="Temperature"
            tooltip="控制模型输出的随机性"
          >
            <Slider
              min={0}
              max={2}
              step={0.1}
              marks={{ 0: '0', 0.7: '0.7', 1: '1', 2: '2' }}
              tooltip={{ formatter: (v) => v?.toFixed(1) }}
            />
          </Form.Item>

          <Form.Item
            name={['model', 'max_tokens']}
            label="Max Tokens"
            tooltip="单次请求最大 token 数"
          >
            <InputNumber min={1} max={128000} style={{ width: '100%' }} />
          </Form.Item>

          <Divider />

          {/* ── Resource Specification ── */}
          <Title level={5} style={{ color: 'var(--oh-text)', marginBottom: 16 }}>资源规格</Title>

          <Form.Item name="resource_spec" label="资源级别">
            <Radio.Group options={RESOURCE_RADIO_OPTIONS} optionType="button" />
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.resource_spec !== cur.resource_spec}>
            {({ getFieldValue }) => {
              const spec = getFieldValue('resource_spec');
              if (!spec || !RESOURCE_SPECS[spec]) return null;
              const info = RESOURCE_SPECS[spec];
              return (
                <div style={{
                  marginBottom: 24,
                  padding: '8px 12px',
                  borderRadius: 8,
                  backgroundColor: 'var(--oh-bg)',
                  border: '1px solid var(--oh-border)',
                }}>
                  <Text type="secondary" style={{ color: 'var(--oh-text-secondary)' }}>
                    {info.label}: {info.cpu} / {info.ram}
                  </Text>
                </div>
              );
            }}
          </Form.Item>

          <Divider />

          {/* ── Advanced Options ── */}
          <Collapse
            ghost
            items={[{
              key: 'advanced',
              label: <Title level={5} style={{ margin: 0, color: 'var(--oh-text)' }}>高级选项</Title>,
              children: (
                <>
                  <Form.Item
                    name={['config', 'system_prompt']}
                    label="System Prompt"
                    tooltip="Agent 的系统提示词"
                  >
                    <TextArea rows={8} placeholder="输入系统提示词（可选）" />
                  </Form.Item>

                  <Form.Item
                    name={['config', 'permission_mode']}
                    label="Permission Mode"
                    tooltip="Agent 操作权限模式"
                  >
                    <Select options={PERMISSION_OPTIONS} placeholder="选择权限模式" />
                  </Form.Item>
                </>
              ),
            }]}
          />

          <Divider />

          {/* ── Actions ── */}
          <Form.Item style={{ marginBottom: 0 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button size="large" onClick={handleCancel}>取消</Button>
              <Button type="primary" htmlType="submit" size="large" loading={submitting}>
                创建 Agent
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
