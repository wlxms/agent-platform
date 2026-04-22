import { Typography, Breadcrumb } from 'antd';
import { Link } from 'react-router-dom';

interface PageHeaderProps {
  title: string;
  extra?: React.ReactNode;
  breadcrumb?: Array<{ title: string; path?: string }>;
}

export default function PageHeader({ title, extra, breadcrumb }: PageHeaderProps) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16,
      }}
    >
      <div>
        {breadcrumb && breadcrumb.length > 0 && (
          <Breadcrumb style={{ marginBottom: 8 }}>
            {breadcrumb.map((item, idx) => (
              <Breadcrumb.Item key={idx}>
                {item.path ? <Link to={item.path}>{item.title}</Link> : item.title}
              </Breadcrumb.Item>
            ))}
          </Breadcrumb>
        )}
        <Typography.Title level={4} style={{ margin: 0 }}>
          {title}
        </Typography.Title>
      </div>
      {extra && <div>{extra}</div>}
    </div>
  );
}
