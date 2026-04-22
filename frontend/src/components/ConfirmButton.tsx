import { useState } from 'react';
import { Popconfirm, Button } from 'antd';
import type { ButtonProps } from 'antd';

interface ConfirmButtonProps {
  title: string;
  description?: string;
  onConfirm: () => void | Promise<void>;
  children: React.ReactNode;
  buttonProps?: ButtonProps;
}

export default function ConfirmButton({ title, description, onConfirm, children, buttonProps }: ConfirmButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Popconfirm title={title} description={description} onConfirm={handleConfirm} okText="确认" cancelText="取消">
      <Button loading={loading} {...buttonProps}>
        {children}
      </Button>
    </Popconfirm>
  );
}
