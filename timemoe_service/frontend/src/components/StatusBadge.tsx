import { Alert, Badge, Space, Tooltip, Typography } from 'antd';
import { useHealthQuery } from '../api/hooks';

const StatusBadge = () => {
  const { data, isLoading, isError, error } = useHealthQuery();

  if (isLoading) {
    return <Badge status="processing" text="检查中" />;
  }

  if (isError) {
    const message = (error as any)?.message || '不可用';
    return (
      <Tooltip title={message}>
        <Badge status="error" text="服务异常" />
      </Tooltip>
    );
  }

  const healthy = data?.status === 'healthy' && data?.model_loaded;
  return (
    <Space size="small">
      <Badge status={healthy ? 'success' : 'warning'} text={healthy ? '在线' : '未加载模型'} />
      {data?.device && (
        <Tooltip
          title={
            <Space direction="vertical" size={2}>
              <Typography.Text type="secondary">版本: {data.version}</Typography.Text>
              <Typography.Text type="secondary">设备: {data.device}</Typography.Text>
            </Space>
          }
        >
          <Typography.Text type="secondary">{data.device}</Typography.Text>
        </Tooltip>
      )}
    </Space>
  );
};

export default StatusBadge;
