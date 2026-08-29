import { useState, useEffect } from 'react';
import type { ExtractRequest, JobResponse, Contract } from './types';
import { extractContractAsync, getJobStatus, listContracts } from './api/client';

function App() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobResponse | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchContracts = async () => {
    try {
      const response = await listContracts();
      setContracts(response.items);
    } catch (err: unknown) {
      console.error('Failed to fetch contracts', err);
    }
  };

  useEffect(() => {
    void fetchContracts();
  }, []);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;
    
    const checkStatus = async () => {
      try {
        if (!jobId) return;
        const status = await getJobStatus(jobId);
        setJobStatus(status);
        
        if (status.status === 'COMPLETED' || status.status === 'FAILED') {
          setLoading(false);
          if (interval) clearInterval(interval);
          
          if (status.status === 'COMPLETED') {
            fetchContracts();
            setText('');
          } else if (status.status === 'FAILED') {
            setError(status.error_message || 'Extraction failed');
          }
        }
      } catch (err: unknown) {
        console.error(err);
        setLoading(false);
        if (interval) clearInterval(interval);
        setError('Failed to fetch job status');
      }
    };

    if (jobId && (jobStatus?.status === 'PENDING' || jobStatus?.status === 'PROCESSING')) {
      interval = setInterval(checkStatus, 2000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [jobId, jobStatus?.status]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    
    setLoading(true);
    setError(null);
    setJobId(null);
    setJobStatus(null);
    
    try {
      const payload: ExtractRequest = { text };
      const response = await extractContractAsync(payload);
      setJobId(response.id);
      setJobStatus(response);
    } catch (err: unknown) {
      if (typeof err === 'object' && err !== null && 'response' in err) {
         const axiosErr = err as { response: { data: { detail: string } }, message: string };
         setError(axiosErr.response?.data?.detail || axiosErr.message || 'An error occurred');
      } else {
         setError('An error occurred');
      }
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
            Legal Document Processor
          </h1>
          <p className="mt-3 max-w-2xl mx-auto text-xl text-gray-500 sm:mt-4">
            Extract structured data from commercial real estate leases.
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="rounded-md bg-red-50 p-4 shadow-sm border border-red-200">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>{error}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          
          {/* Left Column: Input Form */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                New Extraction
              </h3>
              <div className="mt-2 max-w-xl text-sm text-gray-500">
                <p>Paste your lease agreement text below.</p>
              </div>
              <form className="mt-5 sm:flex sm:items-start flex-col space-y-4" onSubmit={handleSubmit}>
                <div className="w-full">
                  <label htmlFor="text" className="sr-only">Lease Text</label>
                  <textarea
                    id="text"
                    name="text"
                    rows={8}
                    className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md p-2 border"
                    placeholder="MEMORANDUM OF LEASE..."
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    disabled={loading}
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading || !text.trim()}
                  className="w-full sm:w-auto inline-flex items-center justify-center px-4 py-2 border border-transparent shadow-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  {loading ? 'Processing...' : 'Extract'}
                </button>
              </form>

              {/* Job Status Indicator */}
              {jobStatus && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-700">Status:</span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      jobStatus.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                      jobStatus.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800 animate-pulse'
                    }`}>
                      {jobStatus.status}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Results Table */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
             <div className="px-4 py-5 sm:px-6 flex justify-between items-center border-b border-gray-200">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Processed Contracts
              </h3>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                Total: {contracts.length}
              </span>
            </div>
            
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Parties</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rent</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {contracts.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                        No contracts processed yet.
                      </td>
                    </tr>
                  ) : (
                    contracts.map((contract) => (
                      <tr key={contract.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{contract.lessee}</div>
                          <div className="text-sm text-gray-500">from {contract.lessor}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">{contract.contract_duration_days} days</div>
                          <div className="text-sm text-gray-500">{contract.commencement_date} to {contract.expiration_date}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">{contract.monthly_rent.toLocaleString()} {contract.currency}</div>
                          <div className="text-sm text-gray-500">{contract.termination_notice_period}d notice</div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default App;
