import { Progress, Space, Typography } from 'antd';
import type { Contributor } from '../api/types';

interface Props {
  data?: Contributor[];
}

const ContributorsBar: React.FC<Props> = ({ data }) => {
  if (!data || data.length === 0) return null;
  const sorted = [...data].sort((a, b) => b.weight - a.weight).slice(0, 5);
  return (
    <Space direction="vertical" style={{ width: '100%' }} size="small">
      {sorted.map((item) => (
        <div key={item.metric} style={{ width: '100%' }}>
          <Typography.Text strong style={{ marginRight: 8 }}>{item.metric}</Typography.Text>
          <Progress
            percent={Math.min(100, Number((item.weight * 100).toFixed(1)))}
            strokeColor={{
              '0%': '#1890ff',
              '100%': '#52c41a',
            }}
            showInfo
          />
        </div>
      ))}
    </Space>
  );
};

export default ContributorsBar;
