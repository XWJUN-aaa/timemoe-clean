export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface DeviceMetrics {
  voltage?: number;
  temperature?: number;
  memory_usage?: number;
  cpu_usage?: number;
  port_errors?: number;
  restart_count?: number;
  uptime?: number;
}

export interface DeviceMetadata {
  vendor?: string;
  model?: string;
  batch?: string;
  sw_version?: string;
  hw_version?: string;
  region?: string;
  install_date?: string;
}

export interface AgingRequest {
  device_id: string;
  timestamp: string;
  metrics: DeviceMetrics;
  metadata?: DeviceMetadata;
  historical_data?: Record<string, any>[];
}

export interface FaultRequest {
  device_id: string;
  timestamp: string;
  metrics: DeviceMetrics;
  metadata: DeviceMetadata;
  historical_data?: Record<string, any>[];
}

export interface BatchRequest {
  devices: AgingRequest[];
}

export interface AgingForecastPoint {
  timestamp: string;
  temperature: number;
  health_index: number;
}

export interface FaultForecastPoint {
  timestamp: string;
  temperature: number;
  fault_probability: number;
}

export interface Contributor {
  metric: string;
  weight: number;
}

export interface AgingResult {
  device_id: string;
  health_index: number;
  tte_hours?: number;
  rul_hours?: number;
  risk_level: RiskLevel;
  contributors: Contributor[];
  prediction_time: string;
  forecast: AgingForecastPoint[];
  forecast_interval_hours: number;
  forecast_horizon_hours: number;
  memory_usage?: number;
  cpu_usage?: number;
  voltage?: number;
  temperature?: number;
}

export interface FaultTrendResult {
  device_id: string;
  prob_7d: number;
  prob_14d: number;
  prob_30d: number;
  risk_level: RiskLevel;
  explanation?: string;
  prediction_time: string;
  forecast: FaultForecastPoint[];
  forecast_interval_hours: number;
  forecast_horizon_hours: number;
  memory_usage?: number;
  cpu_usage?: number;
  voltage?: number;
  temperature?: number;
}

export interface AgingResponse {
  success: boolean;
  result?: AgingResult;
  message?: string;
}

export interface FaultResponse {
  success: boolean;
  result?: FaultTrendResult;
  message?: string;
}

export interface BatchResponse {
  success: boolean;
  results: AgingResult[];
  failed_count: number;
  message?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  model_loaded: boolean;
  device: string;
  timestamp: string;
}

export interface ApiError {
  status?: number;
  message: string;
  detail?: any;
}
