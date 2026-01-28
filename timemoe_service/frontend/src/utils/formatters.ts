export const formatHoursToDH = (hours?: number | null) => {
  if (hours === undefined || hours === null) return '—';
  const h = Math.max(0, Math.round(hours));
  const days = Math.floor(h / 24);
  const remain = h % 24;
  if (days === 0) return `${h} 小时`;
  return `${days} 天 ${remain} 小时`;
};

export const formatPercent = (value?: number, digits = 1) => {
  if (value === undefined || value === null || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(digits)}%`;
};

export const formatNumber = (value?: number, digits = 2) => {
  if (value === undefined || value === null || Number.isNaN(value)) return '—';
  return value.toFixed(digits);
};
