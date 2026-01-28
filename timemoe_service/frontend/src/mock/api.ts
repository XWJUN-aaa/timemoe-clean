import type {
  AgingRequest,
  AgingResponse,
  AgingResult,
  BatchRequest,
  BatchResponse,
  Contributor,
  FaultRequest,
  FaultResponse,
  FaultTrendResult,
  HealthResponse,
  RiskLevel,
} from '../api/types';
import { clamp, seededRandomFromKey } from './random';

const delay = async (ms: number) => {
  const safeMs = Number.isFinite(ms) ? Math.max(0, ms) : 0;
  if (safeMs <= 0) return;
  await new Promise<void>((resolve) => setTimeout(resolve, safeMs));
};

const pickRiskLevelByHealth = (healthIndex: number): RiskLevel => {
  if (healthIndex < 40) return 'critical';
  if (healthIndex < 55) return 'high';
  if (healthIndex < 70) return 'medium';
  return 'low';
};

const pickRiskLevelByProb = (prob: number): RiskLevel => {
  if (prob >= 0.65) return 'critical';
  if (prob >= 0.45) return 'high';
  if (prob >= 0.25) return 'medium';
  return 'low';
};

const buildContributors = (penalties: Record<string, number>): Contributor[] => {
  const entries = Object.entries(penalties).filter(([, value]) => value > 0);
  const total = entries.reduce((sum, [, value]) => sum + value, 0) || 1;
  return entries
    .map(([metric, value]) => ({ metric, weight: Number((value / total).toFixed(4)) }))
    .sort((a, b) => b.weight - a.weight);
};

const toIso = (d: Date) => d.toISOString();

const hoursFromNow = (startIso: string, hours: number): string => {
  const base = new Date(startIso);
  return toIso(new Date(base.getTime() + hours * 3600 * 1000));
};

const resolveTemperature = (payload: { metrics?: any; historical_data?: any[] }, rngKey: string): number => {
  const direct = Number(payload?.metrics?.temperature);
  if (Number.isFinite(direct)) return direct;

  const historyTemps = (payload?.historical_data || [])
    .map((row) => Number((row as any)?.temperature))
    .filter((v) => Number.isFinite(v));
  if (historyTemps.length) {
    const avg = historyTemps.reduce((a, b) => a + b, 0) / historyTemps.length;
    return avg;
  }

  const rng = seededRandomFromKey(`${rngKey}:temperature`);
  return Number((55 + rng.normal(0, 6)).toFixed(1));
};

const resolveVoltage = (payload: { metrics?: any }, rngKey: string): number => {
  const direct = Number(payload?.metrics?.voltage);
  if (Number.isFinite(direct)) return direct;
  const rng = seededRandomFromKey(`${rngKey}:voltage`);
  return Number((48 + rng.normal(0, 0.5)).toFixed(2));
};

const resolveRatio = (value: unknown, defaultValue: number): number => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return defaultValue;
  // 兼容 0-100 的输入
  if (numeric > 1) return clamp(numeric / 100, 0, 1);
  return clamp(numeric, 0, 1);
};

const computeHealthIndex = (payload: AgingRequest, temperature: number, voltage: number): { health: number; penalties: Record<string, number> } => {
  const cpu = resolveRatio(payload.metrics?.cpu_usage, 0.25);
  const memory = resolveRatio(payload.metrics?.memory_usage, 0.35);
  const portErrors = Math.max(0, Number(payload.metrics?.port_errors ?? 0));
  const restarts = Math.max(0, Number(payload.metrics?.restart_count ?? 0));

  const penalties: Record<string, number> = {};
  const tempPenalty = Math.max(0, temperature - 45) * 0.9;
  const cpuPenalty = cpu * 22;
  const memoryPenalty = memory * 16;
  const portPenalty = portErrors * 2.5;
  const restartPenalty = restarts * 6;
  const voltagePenalty = Math.abs(voltage - 48) * 3.5;

  penalties.temperature = tempPenalty;
  penalties.cpu_usage = cpuPenalty;
  penalties.memory_usage = memoryPenalty;
  penalties.port_errors = portPenalty;
  penalties.restart_count = restartPenalty;
  penalties.voltage = voltagePenalty;

  const totalPenalty = Object.values(penalties).reduce((a, b) => a + b, 0);
  const health = clamp(96 - totalPenalty, 0, 100);
  return { health: Number(health.toFixed(1)), penalties };
};

const estimateRulHours = (healthIndex: number): { rul: number; tte: number } => {
  const rul = clamp(healthIndex, 0, 100) * 8; // 0..800 小时
  const tte = Math.max(12, rul * 0.65);
  return { rul: Math.round(rul), tte: Math.round(tte) };
};

export const mockFetchHealth = async (): Promise<HealthResponse> => {
  await delay(Number(import.meta.env.VITE_MOCK_DELAY_MS || 120));
  return {
    status: 'healthy',
    version: 'mock-0.1.0',
    model_loaded: true,
    device: 'mock',
    timestamp: toIso(new Date()),
  };
};

export const mockPredictAging = async (payload: AgingRequest): Promise<AgingResponse> => {
  await delay(Number(import.meta.env.VITE_MOCK_DELAY_MS || 240));

  const key = payload.device_id || 'demo';
  const temperature = resolveTemperature(payload, key);
  const voltage = resolveVoltage(payload, key);

  const { health, penalties } = computeHealthIndex(payload, temperature, voltage);
  const riskLevel = pickRiskLevelByHealth(health);
  const { rul, tte } = estimateRulHours(health);

  const horizonHours = 72;
  const intervalHours = 6;
  const steps = Math.floor(horizonHours / intervalHours) + 1;
  const predictionTime = payload.timestamp || toIso(new Date());

  const rng = seededRandomFromKey(`${key}:${predictionTime}:aging`);
  const drift = (100 - health) / steps;

  const forecast = Array.from({ length: steps }).map((_, i) => {
    const t = i * intervalHours;
    const temp = clamp(temperature + rng.normal(0, 0.6) + i * 0.15, 30, 95);
    const h = clamp(health - drift * i + rng.normal(0, 0.8), 0, 100);
    return {
      timestamp: hoursFromNow(predictionTime, t),
      temperature: Number(temp.toFixed(1)),
      health_index: Number(h.toFixed(1)),
    };
  });

  const result: AgingResult = {
    device_id: payload.device_id,
    health_index: health,
    tte_hours: tte,
    rul_hours: rul,
    risk_level: riskLevel,
    contributors: buildContributors(penalties),
    prediction_time: predictionTime,
    forecast,
    forecast_interval_hours: intervalHours,
    forecast_horizon_hours: horizonHours,
    temperature: Number(temperature.toFixed(1)),
    voltage: Number(voltage.toFixed(2)),
    cpu_usage: resolveRatio(payload.metrics?.cpu_usage, 0.25),
    memory_usage: resolveRatio(payload.metrics?.memory_usage, 0.35),
  };

  return { success: true, result };
};

export const mockPredictFault = async (payload: FaultRequest): Promise<FaultResponse> => {
  await delay(Number(import.meta.env.VITE_MOCK_DELAY_MS || 260));

  const key = payload.device_id || 'demo';
  const temperature = resolveTemperature(payload, key);
  const voltage = resolveVoltage(payload, key);

  const cpu = resolveRatio(payload.metrics?.cpu_usage, 0.25);
  const memory = resolveRatio(payload.metrics?.memory_usage, 0.35);
  const portErrors = Math.max(0, Number(payload.metrics?.port_errors ?? 0));
  const restarts = Math.max(0, Number(payload.metrics?.restart_count ?? 0));

  const base =
    0.06 +
    Math.max(0, temperature - 50) * 0.006 +
    cpu * 0.22 +
    memory * 0.18 +
    portErrors * 0.02 +
    restarts * 0.03 +
    Math.abs(voltage - 48) * 0.05;

  const prob7 = clamp(base, 0, 1);
  const prob14 = clamp(prob7 + 0.08, 0, 1);
  const prob30 = clamp(prob14 + 0.14, 0, 1);
  const riskLevel = pickRiskLevelByProb(prob30);

  const horizonHours = 168;
  const intervalHours = 12;
  const steps = Math.floor(horizonHours / intervalHours) + 1;
  const predictionTime = payload.timestamp || toIso(new Date());

  const rng = seededRandomFromKey(`${key}:${predictionTime}:fault`);
  const forecast = Array.from({ length: steps }).map((_, i) => {
    const t = i * intervalHours;
    const temp = clamp(temperature + rng.normal(0, 0.8) + i * 0.1, 30, 95);
    const p = clamp(prob7 + (prob30 - prob7) * (i / Math.max(1, steps - 1)) + rng.normal(0, 0.015), 0, 1);
    return {
      timestamp: hoursFromNow(predictionTime, t),
      temperature: Number(temp.toFixed(1)),
      fault_probability: Number(p.toFixed(3)),
    };
  });

  const result: FaultTrendResult = {
    device_id: payload.device_id,
    prob_7d: Number(prob7.toFixed(3)),
    prob_14d: Number(prob14.toFixed(3)),
    prob_30d: Number(prob30.toFixed(3)),
    risk_level: riskLevel,
    explanation: `综合温度、资源占用与端口错误估算故障风险（演示用模拟结果）`,
    prediction_time: predictionTime,
    forecast,
    forecast_interval_hours: intervalHours,
    forecast_horizon_hours: horizonHours,
    temperature: Number(temperature.toFixed(1)),
    voltage: Number(voltage.toFixed(2)),
    cpu_usage: cpu,
    memory_usage: memory,
  };

  return { success: true, result };
};

export const mockBatchPredict = async (payload: BatchRequest): Promise<BatchResponse> => {
  await delay(Number(import.meta.env.VITE_MOCK_DELAY_MS || 320));
  const results: AgingResult[] = [];
  for (const device of payload.devices || []) {
    const response = await mockPredictAging(device);
    if (response.success && response.result) {
      results.push(response.result);
    }
  }
  return {
    success: true,
    results,
    failed_count: Math.max(0, (payload.devices?.length || 0) - results.length),
  };
};

