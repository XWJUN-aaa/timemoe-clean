import type { RiskLevel } from '../api/types';

export const riskColorMap: Record<RiskLevel, string> = {
  low: '#52c41a',
  medium: '#fadb14',
  high: '#fa8c16',
  critical: '#f5222d',
};

export const riskLabelMap: Record<RiskLevel, string> = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '严重',
};

export const riskDescription = (level: RiskLevel) => {
  switch (level) {
    case 'low':
      return '健康良好';
    case 'medium':
      return '关注运行状况';
    case 'high':
      return '存在风险，建议检查';
    case 'critical':
      return '高风险，建议立即处理';
    default:
      return '';
  }
};
