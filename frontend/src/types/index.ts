export interface Contract {
  id: number;
  lessor: string;
  lessee: string;
  commencement_date: string;
  expiration_date: string;
  monthly_rent: number;
  currency: string;
  termination_notice_period: number;
  contract_duration_days: number;
  created_at: string;
}

export interface ContractListResponse {
  total: number;
  items: Contract[];
}

export interface JobResponse {
  id: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  provider?: string;
  model?: string;
  contract_id?: number;
  contract?: Contract;
  error_message?: string;
  error_code?: string;
  created_at: string;
  completed_at?: string;
}

export interface ExtractRequest {
  text: string;
}

export interface ErrorResponse {
  detail: string;
  error_code: string;
  details?: any;
}
