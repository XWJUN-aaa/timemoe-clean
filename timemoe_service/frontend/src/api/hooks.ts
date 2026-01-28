import { useQuery, useMutation } from '@tanstack/react-query';
import {
  fetchHealth,
  predictAging,
  predictFault,
  batchPredict,
} from './client';
import type {
  AgingRequest,
  AgingResponse,
  FaultRequest,
  FaultResponse,
  BatchRequest,
  BatchResponse,
} from './types';

export const useHealthQuery = () =>
  useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 5000,
    retry: 1,
  });

export const useAgingMutation = () =>
  useMutation<{ data: AgingResponse }, unknown, AgingRequest>({
    mutationFn: async (payload) => ({ data: await predictAging(payload) }),
  });

export const useFaultMutation = () =>
  useMutation<{ data: FaultResponse }, unknown, FaultRequest>({
    mutationFn: async (payload) => ({ data: await predictFault(payload) }),
  });

export const useBatchMutation = () =>
  useMutation<{ data: BatchResponse }, unknown, BatchRequest>({
    mutationFn: async (payload) => ({ data: await batchPredict(payload) }),
  });
