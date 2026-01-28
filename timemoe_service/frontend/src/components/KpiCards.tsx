import { Card, Col, Row, Space, Statistic, Tag, Typography } from 'antd';
import type { AgingResult, FaultTrendResult } from '../api/types';
import { riskColorMap, riskDescription, riskLabelMap } from '../utils/risk';
import { formatHoursToDH, formatPercent, formatNumber } from '../utils/formatters';

interface Props {
  mode: 'aging' | 'fault';
  aging?: AgingResult | null;
  fault?: FaultTrendResult | null;
}

const KpiCards: React.FC<Props> = ({ mode, aging, fault }) => {
  const isAging = mode === 'aging';
  const riskLevel = isAging ? aging?.risk_level : fault?.risk_level;
  const cardTitle = isAging ? '老化预测' : '故障趋势';
  const primaryValue = isAging ? aging?.health_index : fault?.prob_7d;
  const secondaryValue = isAging ? aging?.rul_hours : fault?.prob_30d;

  if (!riskLevel) return null;

  return (
    <Row gutter={12} style={{ marginBottom: 12 }}>
      <Col span={8}>
        <Card size="small" title={cardTitle}>
          <Space direction="vertical">
            <Tag color={riskColorMap[riskLevel]}>{riskLabelMap[riskLevel]}</Tag>
            <Typography.Text type="secondary">{riskDescription(riskLevel)}</Typography.Text>
          </Space>
        </Card>
      </Col>
      <Col span={8}>
        <Card size="small" title={isAging ? '健康指数' : '7天故障率'}>
          {isAging ? (
            <Statistic value={primaryValue ?? 0} precision={1} />
          ) : (
            <Typography.Text>{formatPercent(primaryValue as number | undefined)}</Typography.Text>
          )}
        </Card>
      </Col>
      <Col span={8}>
        <Card size="small" title={isAging ? '剩余寿命 (RUL)' : '30天故障率'}>
          {isAging ? (
            <Typography.Text>{formatHoursToDH(secondaryValue)}</Typography.Text>
          ) : (
            <Statistic value={formatPercent(secondaryValue as number | undefined)} />
          )}
        </Card>
      </Col>
    </Row>
  );
};

export default KpiCards;
