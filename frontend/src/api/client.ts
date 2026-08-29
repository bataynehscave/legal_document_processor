import axios, { AxiosError } from 'axios';
import type { AxiosResponse } from 'axios';
import type { ExtractRequest, JobResponse, ContractListResponse } from '../types';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor to handle common errors gracefully
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    // You can handle global error logging or notification triggering here
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const extractContractAsync = async (data: ExtractRequest): Promise<JobResponse> => {
  const response = await apiClient.post<JobResponse>('/extract/async', data);
  return response.data;
};

export const getJobStatus = async (jobId: string): Promise<JobResponse> => {
  const response = await apiClient.get<JobResponse>(`/jobs/${jobId}`);
  return response.data;
};

export const listContracts = async (): Promise<ContractListResponse> => {
  const response = await apiClient.get<ContractListResponse>('/contracts');
  return response.data;
};
