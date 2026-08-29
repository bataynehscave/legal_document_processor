import axios, { AxiosError } from 'axios';
import type { AxiosResponse } from 'axios';
import type { ExtractRequest, JobResponse, ContractListResponse, Contract } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 35000,
});

// Response interceptor to handle common errors gracefully
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const extractContractSync = async (data: ExtractRequest): Promise<Contract> => {
  const response = await apiClient.post<Contract>('/extract', data);
  return response.data;
};

export const extractContractAsync = async (data: ExtractRequest): Promise<JobResponse> => {
  const response = await apiClient.post<JobResponse>('/extract/async', data);
  return response.data;
};

export const getJobStatus = async (jobId: string): Promise<JobResponse> => {
  const response = await apiClient.get<JobResponse>(`/jobs/${jobId}`);
  return response.data;
};

export const listContracts = async (params?: {
  search?: string;
  currency?: string;
  min_rent?: number;
  max_rent?: number;
}): Promise<ContractListResponse> => {
  const response = await apiClient.get<ContractListResponse>('/contracts', { params });
  return response.data;
};

export const getContractById = async (id: number): Promise<Contract> => {
  const response = await apiClient.get<Contract>(`/contracts/${id}`);
  return response.data;
};

export const deleteContract = async (id: number): Promise<void> => {
  await apiClient.delete(`/contracts/${id}`);
};

export default apiClient;
