import axios, { AxiosError } from 'axios';
import type {
  AgingRequest,
  AgingResponse,
  FaultRequest,
  FaultResponse,
  BatchRequest,
  BatchResponse,
  HealthResponse,
  ApiError,
} from './types';
import {
  mockBatchPredict,
  mockFetchHealth,
  mockPredictAging,
  mockPredictFault,
} from '../mock/api';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const useMock = import.meta.env.VITE_USE_MOCK === 'true';

export const apiClient = axios.create({
  baseURL,
  timeout: 60000,
});

const toApiError = (error: unknown): ApiError => {
  if (axios.isAxiosError(error)) {
    const err = error as AxiosError<any>;
    return {
      status: err.response?.status,
      message: (err.response?.data as any)?.detail || err.message,
      detail: err.response?.data,
    };
  }
  return { message: (error as Error)?.message || '未知错误' };
};

export const fetchHealth = async (): Promise<HealthResponse> => {
  if (useMock) return mockFetchHealth();
  try {
    const { data } = await apiClient.get<HealthResponse>('/health');
    return data;
  } catch (error) {
    throw toApiError(error);
  }
};

export const predictAging = async (payload: AgingRequest): Promise<AgingResponse> => {
  if (useMock) return mockPredictAging(payload);
  try {
    const { data } = await apiClient.post<AgingResponse>('/predict/aging', payload);
    return data;
  } catch (error) {
    throw toApiError(error);
  }
};

export const predictFault = async (payload: FaultRequest): Promise<FaultResponse> => {
  if (useMock) return mockPredictFault(payload);
  try {
    const { data } = await apiClient.post<FaultResponse>('/predict/fault', payload);
    return data;
  } catch (error) {
    throw toApiError(error);
  }
};

export const batchPredict = async (payload: BatchRequest): Promise<BatchResponse> => {
  if (useMock) return mockBatchPredict(payload);
  try {
    const { data } = await apiClient.post<BatchResponse>('/batch/predict', payload);
    return data;
  } catch (error) {
    throw toApiError(error);
  }
};
