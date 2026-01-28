import { Layout, Menu, Typography, Space, Flex } from 'antd';
import { LaptopOutlined, AppstoreOutlined, HistoryOutlined } from '@ant-design/icons';
import { Link, Route, Routes, useLocation } from 'react-router-dom';
import WorkbenchPage from './pages/Workbench/WorkbenchPage';
import BatchPage from './pages/Batch/BatchPage';
import HistoryPage from './pages/History/HistoryPage';
import StatusBadge from './components/StatusBadge';

const { Header, Content } = Layout;

const App = () => {
  const location = useLocation();
  const selectedKey = (() => {
    if (location.pathname.startsWith('/batch')) return 'batch';
    if (location.pathname.startsWith('/history')) return 'history';
    return 'workbench';
  })();

  const items = [
    { key: 'workbench', label: <Link to="/">智能诊断台</Link>, icon: <LaptopOutlined /> },
    { key: 'batch', label: <Link to="/batch">批量巡检</Link>, icon: <AppstoreOutlined /> },
    { key: 'history', label: <Link to="/history">历史记录</Link>, icon: <HistoryOutlined /> },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', borderBottom: '1px solid #f0f0f0' }}>
        <Flex align="center" justify="space-between">
          <Space align="center" size="large">
            <Typography.Title level={4} style={{ margin: 0 }}>
              TimeMoE 推理服务控制台
            </Typography.Title>
            <StatusBadge />
          </Space>
          <Menu mode="horizontal" selectedKeys={[selectedKey]} items={items} style={{ minWidth: 360 }} />
        </Flex>
      </Header>
      <Content style={{ padding: '16px 24px 32px' }}>
        <Routes>
          <Route path="/" element={<WorkbenchPage />} />
          <Route path="/batch" element={<BatchPage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </Content>
    </Layout>
  );
};

export default App;
