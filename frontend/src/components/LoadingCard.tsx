import { Card, Skeleton } from 'antd';

interface LoadingCardProps {
  rows?: number;
}

export default function LoadingCard({ rows = 3 }: LoadingCardProps) {
  return (
    <Card>
      <Skeleton paragraph={{ rows }} active />
    </Card>
  );
}
