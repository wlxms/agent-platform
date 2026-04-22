import { useState, useCallback } from 'react';
import { Tooltip, Button, message } from 'antd';
import { CopyOutlined } from '@ant-design/icons';

interface CopyButtonProps {
  text: string;
  icon?: boolean;
}

export default function CopyButton({ text, icon = true }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      message.success('已复制');
      setTimeout(() => setCopied(false), 1500);
    } catch {
      message.error('复制失败');
    }
  }, [text]);

  if (icon) {
    return (
      <Tooltip title={copied ? '已复制' : '复制'}>
        <Button type="text" size="small" icon={<CopyOutlined />} onClick={handleCopy} />
      </Tooltip>
    );
  }

  return (
    <Button type="text" size="small" onClick={handleCopy}>
      {copied ? '已复制' : '复制'}
    </Button>
  );
}
