import React from 'react';
import ReactECharts from 'echarts-for-react';
import dayjs from 'dayjs';
import type { AgingResult, FaultTrendResult } from '../api/types';
import { riskColorMap } from '../utils/risk';

interface Props {
  mode: 'aging' | 'fault';
  aging?: AgingResult | null;
  fault?: FaultTrendResult | null;
}

const ForecastChart: React.FC<Props> = ({ mode, aging, fault }) => {
  const isAging = mode === 'aging';
  const predictionTime = isAging ? aging?.prediction_time : fault?.prediction_time;

  const forecast = isAging ? aging?.forecast || [] : fault?.forecast || [];
  const xData = forecast.map((item) => dayjs(item.timestamp).format('MM-DD HH:mm'));

  const series = isAging
    ? [
        {
          name: '健康指数',
          type: 'line',
          yAxisIndex: 1,
          data: forecast.map((f) => f.health_index),
          smooth: true,
          symbol: 'circle',
          lineStyle: { width: 2 },
        },
        {
          name: '温度',
          type: 'line',
          yAxisIndex: 0,
          data: forecast.map((f) => f.temperature),
          smooth: true,
          symbol: 'none',
          lineStyle: { type: 'dashed' },
        },
      ]
    : [
        {
          name: '故障概率',
          type: 'line',
          yAxisIndex: 1,
          data: forecast.map((f) => f.fault_probability),
          smooth: true,
          symbol: 'circle',
          lineStyle: { width: 2 },
        },
        {
          name: '温度',
          type: 'line',
          yAxisIndex: 0,
          data: forecast.map((f) => f.temperature),
          smooth: true,
          symbol: 'none',
          lineStyle: { type: 'dashed' },
        },
      ];

  const markLine = predictionTime
    ? {
        symbol: 'none',
        data: [
          {
            xAxis: dayjs(predictionTime).format('MM-DD HH:mm'),
            lineStyle: { color: '#999' },
            label: { formatter: '预测时刻' },
          },
        ],
      }
    : undefined;

  const option = {
    tooltip: {
      trigger: 'axis',
    },
    legend: {
      data: series.map((s) => s.name),
    },
    grid: { left: 50, right: 60, bottom: 60, top: 40 },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { rotate: 30 },
    },
    yAxis: [
      {
        type: 'value',
        name: '温度',
        axisLabel: { formatter: '{value}°' },
      },
      {
        type: 'value',
        name: isAging ? '健康指数' : '故障概率',
        min: isAging ? 0 : 0,
        max: isAging ? 100 : 1,
        axisLabel: { formatter: isAging ? '{value}' : '{value}' },
      },
    ],
    series: series.map((s) => ({ ...s, markLine })),
  };

  if (!forecast.length) {
    return null;
  }

  return <ReactECharts style={{ height: 320 }} option={option} />;
};

export default ForecastChart;
