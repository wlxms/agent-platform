import { RouterProvider } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { ThemeProvider } from '@/theme';
import { router } from '@/router';

export default function App() {
  return (
    <ThemeProvider>
      <ConfigProvider locale={zhCN}>
        <RouterProvider router={router} />
      </ConfigProvider>
    </ThemeProvider>
  );
}
