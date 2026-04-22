import { Tag } from 'antd';
import type { AgentStatus } from '@/types';

const STATUS_COLOR_MAP: Record<AgentStatus, string> = {
  ready: 'success',
  running: 'processing',
  creating: 'warning',
  seeding: 'warning',
  stopping: 'warning',
  stopped: 'default',
  failed: 'error',
};

interface StatusBadgeProps {
  status: AgentStatus;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  return <Tag color={STATUS_COLOR_MAP[status]}>{status}</Tag>;
}
