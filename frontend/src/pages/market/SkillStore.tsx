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
import type { Skill, AgentInstance } from '@/types';

const { Text, Paragraph } = Typography;

const PAGE_SIZE = 12;

export default function SkillStore() {
  const [keyword, setKeyword] = useState('');
  const [skills, setSkills] = useState<Skill[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  // Install modal
  const [installModalOpen, setInstallModalOpen] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [targetAgentId, setTargetAgentId] = useState<string | undefined>(undefined);
  const [agents, setAgents] = useState<AgentInstance[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [installing, setInstalling] = useState(false);

  const fetchSkills = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const res = await marketApi.getSkills({
        keyword: keyword || undefined,
        page: p,
        page_size: PAGE_SIZE,
      });
      setSkills(res.items);
      setTotal(res.total);
    } catch {
      message.error('加载 Skill 列表失败');
    } finally {
      setLoading(false);
    }
  }, [keyword]);

  useEffect(() => {
    fetchSkills(page);
  }, [page, fetchSkills]);

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

  const openInstallModal = (skill: Skill) => {
    setSelectedSkill(skill);
    setTargetAgentId(undefined);
    setInstallModalOpen(true);
    fetchAgents();
  };

  const handleInstall = async () => {
    if (!selectedSkill || !targetAgentId) return;
    setInstalling(true);
    try {
      await agentsApi.installSkill(targetAgentId, { skill_id: selectedSkill.id });
      message.success(`已将 ${selectedSkill.name} 安装到 Agent`);
      setInstallModalOpen(false);
    } catch {
      message.error('安装失败');
    } finally {
      setInstalling(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginBottom: 24, color: 'var(--oh-text)' }}>
        技能商店
      </Typography.Title>

      <Input
        placeholder="搜索 Skill..."
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
        {!loading && skills.length === 0 ? (
          <Empty description="暂无 Skill" />
        ) : (
          <>
            <List
              grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 4 }}
              dataSource={skills}
              renderItem={(skill) => (
                <List.Item>
                  <Card
                    style={{ height: '100%', backgroundColor: 'var(--oh-surface)', borderColor: 'var(--oh-border)' }}
                    actions={[
                      <Button type="primary" size="small" onClick={() => openInstallModal(skill)}>
                        安装
                      </Button>,
                    ]}
                  >
                    <Text strong style={{ color: 'var(--oh-text)', display: 'block', marginBottom: 4 }}>
                      {skill.name}
                    </Text>
                    <Tag color="var(--oh-primary)" style={{ marginBottom: 8 }}>
                      v{skill.version}
                    </Tag>
                    <Paragraph
                      type="secondary"
                      ellipsis={{ rows: 2 }}
                      style={{ color: 'var(--oh-text-secondary)', marginBottom: 8, minHeight: 44 }}
                    >
                      {skill.description}
                    </Paragraph>
                    {skill.author && (
                      <Text type="secondary" style={{ color: 'var(--oh-text-secondary)', fontSize: 12 }}>
                        {skill.author}
                      </Text>
                    )}
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
        title={`安装 ${selectedSkill?.name ?? ''}`}
        open={installModalOpen}
        onOk={handleInstall}
        onCancel={() => setInstallModalOpen(false)}
        confirmLoading={installing}
        okText="确认安装"
        cancelText="取消"
        okButtonProps={{ disabled: !targetAgentId }}
      >
        <div style={{ marginBottom: 16 }}>
          <Text style={{ color: 'var(--oh-text)' }}>选择目标 Agent：</Text>
        </div>
        <Select
          showSearch
          placeholder="选择 Agent"
          loading={agentsLoading}
          style={{ width: '100%' }}
          value={targetAgentId}
          onChange={setTargetAgentId}
          optionFilterProp="label"
          options={agents.map((a) => ({ value: a.id, label: a.name }))}
        />
      </Modal>
    </div>
  );
}
