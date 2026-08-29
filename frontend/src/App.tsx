import { useState, useEffect } from 'react';
import type { ExtractRequest, JobResponse, Contract } from './types';
import { extractContractAsync, getJobStatus, listContracts, getContractById } from './api/client';

const SAMPLE_LEASE_TEXT = `MEMORANDUM OF LEASE
This agreement is entered into this 12th day of May, 2024, by and between Apex Holdings LLC (hereafter the Landlord) and Vertex Tech Solutions Corp (hereafter the Tenant). The property located at Suite 404, Dubai Sports City, is leased for a term starting on June 1st, 2024, and ending exactly two years later on May 31st, 2026. The agreed monthly consideration is 12500.00 AED, payable on the first of each month. Either party may terminate this agreement early by providing at least 90 days written notice to the other party.`;

function App() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobResponse | null>(null);
  const [latestContract, setLatestContract] = useState<Contract | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [selectedContract, setSelectedContract] = useState<Contract | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currencyFilter, setCurrencyFilter] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [errorDetails, setErrorDetails] = useState<any>(null);

  const fetchContracts = async () => {
    try {
      const params: { search?: string; currency?: string } = {};
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (currencyFilter.trim()) params.currency = currencyFilter.trim();
      const response = await listContracts(params);
      setContracts(response.items);
    } catch (err: unknown) {
      console.error('Failed to fetch contracts', err);
    }
  };

  useEffect(() => {
    void fetchContracts();
  }, [searchQuery, currencyFilter]);

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

          if (status.status === 'COMPLETED' && status.contract) {
            setLatestContract(status.contract);
            fetchContracts();
          } else if (status.status === 'FAILED') {
            setError(status.error_message || 'Extraction failed');
            setErrorDetails(status.error_code);
          }
        }
      } catch (err: unknown) {
        console.error(err);
        setLoading(false);
        if (interval) clearInterval(interval);
        setError('Failed to fetch background job status.');
      }
    };

    if (jobId && (jobStatus?.status === 'PENDING' || jobStatus?.status === 'PROCESSING')) {
      interval = setInterval(checkStatus, 1500);
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
    setErrorDetails(null);
    setJobId(null);
    setJobStatus(null);
    setLatestContract(null);

    try {
      const payload: ExtractRequest = { text };
      const response = await extractContractAsync(payload);
      setJobId(response.id);
      setJobStatus(response);
    } catch (err: any) {
      setLoading(false);
      const resData = err.response?.data;
      if (resData) {
        setError(resData.detail || 'An error occurred during extraction.');
        setErrorDetails(resData.details || resData.error_code);
      } else if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Extraction timed out. The LLM service took too long to respond.');
      } else if (!err.response) {
        setError('Backend server unavailable. Make sure the FastAPI service is running on port 8000.');
      } else {
        setError(err.message || 'An unexpected error occurred.');
      }
    }
  };

  const handleViewDetails = async (id: number) => {
    setLoadingDetails(true);
    try {
      const fullContract = await getContractById(id);
      setSelectedContract(fullContract);
    } catch (err: unknown) {
      console.error('Failed to fetch contract details', err);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleLoadSample = () => {
    setText(SAMPLE_LEASE_TEXT);
    setError(null);
    setErrorDetails(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 antialiased">
      {/* Navigation Header */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-10 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
              §
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 leading-tight">Legal Document Processor</h1>
              <p className="text-xs text-slate-500">Commercial Real Estate Lease Extraction Pipeline</p>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-xs">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 font-medium border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse"></span>
              Gemini 3.7 Flash
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Error Alert Box */}
        {error && (
          <div className="rounded-xl bg-red-50 p-4 border border-red-200 shadow-sm transition-all duration-200">
            <div className="flex items-start">
              <div className="shrink-0 text-red-500 mt-0.5 font-bold">⚠️</div>
              <div className="ml-3 flex-1">
                <h3 className="text-sm font-semibold text-red-800">Processing / Validation Error</h3>
                <div className="mt-1 text-sm text-red-700">
                  <p>{error}</p>
                  {errorDetails && (
                    <pre className="mt-2 text-xs bg-red-100/70 p-2 rounded text-red-900 overflow-x-auto">
                      {typeof errorDetails === 'object' ? JSON.stringify(errorDetails, null, 2) : String(errorDetails)}
                    </pre>
                  )}
                </div>
              </div>
              <button
                onClick={() => { setError(null); setErrorDetails(null); }}
                className="text-red-400 hover:text-red-600 text-sm font-bold ml-2"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* Left Column: Extraction Input & Extracted Preview (5 Cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Input Card */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">Contract Ingestion</h2>
                  <p className="text-xs text-slate-500">Paste unstructured commercial lease agreement text</p>
                </div>
                <button
                  type="button"
                  onClick={handleLoadSample}
                  className="text-xs font-medium text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-2.5 py-1.5 rounded-lg transition-colors"
                >
                  Load Sample Lease
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <textarea
                    id="contract-text"
                    rows={9}
                    className="w-full text-xs font-mono p-3.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition resize-none bg-slate-50/50"
                    placeholder="MEMORANDUM OF LEASE... Paste raw lease agreement text here."
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    disabled={loading}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">
                    {text.trim().length} characters
                  </span>
                  <button
                    type="submit"
                    disabled={loading || text.trim().length < 10}
                    className="inline-flex items-center px-4 py-2.5 rounded-xl text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm transition-all focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  >
                    {loading ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                        </svg>
                        Extracting Metadata...
                      </>
                    ) : (
                      'Extract Contract'
                    )}
                  </button>
                </div>
              </form>

              {/* Extraction Job Status Indicator */}
              {jobStatus && (
                <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-mono">Job ID: {jobStatus.id.slice(0, 8)}...</span>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full font-semibold ${
                      jobStatus.status === 'COMPLETED'
                        ? 'bg-emerald-100 text-emerald-800'
                        : jobStatus.status === 'FAILED'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-amber-100 text-amber-800 animate-pulse'
                    }`}
                  >
                    {jobStatus.status}
                  </span>
                </div>
              )}
            </div>

            {/* Latest Extraction Success Card (Requirement 7.1) */}
            {latestContract && (
              <div className="bg-white rounded-2xl shadow-sm border-2 border-emerald-500/30 p-6 space-y-4 bg-linear-to-b from-emerald-50/20 to-white">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center space-x-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                    <h3 className="text-sm font-bold text-slate-900">Extracted Contract Metadata</h3>
                  </div>
                  <span className="text-xs bg-emerald-100 text-emerald-800 font-mono px-2 py-0.5 rounded-md font-semibold">
                    ID #{latestContract.id}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-2.5 bg-slate-50 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">Lessor (Landlord)</span>
                    <span className="font-semibold text-slate-900">{latestContract.lessor}</span>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">Lessee (Tenant)</span>
                    <span className="font-semibold text-slate-900">{latestContract.lessee}</span>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">Commencement Date</span>
                    <span className="font-semibold text-slate-900">{latestContract.commencement_date}</span>
                  </div>
                  <div className="p-2.5 bg-slate-50 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">Expiration Date</span>
                    <span className="font-semibold text-slate-900">{latestContract.expiration_date}</span>
                  </div>
                  <div className="p-2.5 bg-blue-50/50 rounded-xl">
                    <span className="text-blue-500 block text-[10px] uppercase font-bold tracking-wider">Monthly Rent</span>
                    <span className="font-bold text-blue-900 text-sm">{latestContract.monthly_rent.toLocaleString()} {latestContract.currency}</span>
                  </div>
                  <div className="p-2.5 bg-blue-50/50 rounded-xl">
                    <span className="text-blue-500 block text-[10px] uppercase font-bold tracking-wider">Notice Period</span>
                    <span className="font-semibold text-blue-900">{latestContract.termination_notice_period} Days</span>
                  </div>
                  <div className="col-span-2 p-2.5 bg-emerald-50 rounded-xl flex items-center justify-between">
                    <span className="text-emerald-700 text-xs font-medium">Calculated Contract Duration:</span>
                    <span className="font-bold text-emerald-900 text-sm">{latestContract.contract_duration_days} Days</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Contracts List & Filter Table (7 Cols) (Requirement 7.3) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
              {/* Table Header & Search Filter */}
              <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">Processed Contracts</h2>
                  <p className="text-xs text-slate-500">List of verified records stored in SQLite database</p>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    placeholder="Search party..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 focus:ring-1 focus:ring-blue-500 outline-none w-36"
                  />
                  <select
                    value={currencyFilter}
                    onChange={(e) => setCurrencyFilter(e.target.value)}
                    className="text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 focus:ring-1 focus:ring-blue-500 outline-none bg-white"
                  >
                    <option value="">All Currencies</option>
                    <option value="AED">AED</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="GBP">GBP</option>
                  </select>
                  <button
                    onClick={fetchContracts}
                    className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
                    title="Refresh contracts"
                  >
                    🔄
                  </button>
                </div>
              </div>

              {/* Table Content */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50/75 border-b border-slate-100 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                      <th className="py-3 px-4">ID</th>
                      <th className="py-3 px-4">Parties</th>
                      <th className="py-3 px-4">Term & Duration</th>
                      <th className="py-3 px-4">Monthly Rent</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {contracts.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-12 text-center text-slate-400 text-xs">
                          No contracts processed yet. Submit a lease agreement to see results.
                        </td>
                      </tr>
                    ) : (
                      contracts.map((c) => (
                        <tr
                          key={c.id}
                          className="hover:bg-blue-50/40 transition-colors cursor-pointer group"
                          onClick={() => handleViewDetails(c.id)}
                        >
                          <td className="py-3.5 px-4 font-mono font-medium text-slate-500">
                            #{c.id}
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-semibold text-slate-900">{c.lessee}</div>
                            <div className="text-[11px] text-slate-400">Lessor: {c.lessor}</div>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-medium text-slate-800">{c.contract_duration_days} Days</div>
                            <div className="text-[11px] text-slate-400 font-mono">{c.commencement_date} → {c.expiration_date}</div>
                          </td>
                          <td className="py-3.5 px-4 font-semibold text-slate-900">
                            {c.monthly_rent.toLocaleString()} {c.currency}
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleViewDetails(c.id);
                              }}
                              className="text-xs font-semibold text-blue-600 hover:text-blue-800 bg-blue-50 px-2.5 py-1 rounded-md opacity-90 group-hover:opacity-100 transition"
                            >
                              Details
                            </button>
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
      </main>

      {/* Contract Details Modal (Requirement 7.4) */}
      {selectedContract && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-2xl w-full p-6 space-y-6 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <span className="text-xs font-mono text-blue-600 font-semibold bg-blue-50 px-2 py-0.5 rounded">
                  Contract #{selectedContract.id}
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-1">Contract Inspection Details</h3>
              </div>
              <button
                onClick={() => setSelectedContract(null)}
                className="text-slate-400 hover:text-slate-600 font-bold p-1 rounded-lg hover:bg-slate-100"
              >
                ✕
              </button>
            </div>

            {loadingDetails ? (
              <div className="py-12 text-center text-slate-400">Loading details...</div>
            ) : (
              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-slate-50 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Lessor (Landlord)</span>
                    <span className="text-sm font-semibold text-slate-900">{selectedContract.lessor}</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Lessee (Tenant)</span>
                    <span className="text-sm font-semibold text-slate-900">{selectedContract.lessee}</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Commencement Date</span>
                    <span className="text-sm font-semibold text-slate-900">{selectedContract.commencement_date}</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Expiration Date</span>
                    <span className="text-sm font-semibold text-slate-900">{selectedContract.expiration_date}</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Monthly Rent</span>
                    <span className="text-sm font-bold text-blue-600">{selectedContract.monthly_rent.toLocaleString()} {selectedContract.currency}</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-xl">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Termination Notice</span>
                    <span className="text-sm font-semibold text-slate-900">{selectedContract.termination_notice_period} Days</span>
                  </div>
                  <div className="p-3 bg-emerald-50 rounded-xl col-span-2 flex items-center justify-between">
                    <div>
                      <span className="text-emerald-700 block text-[10px] uppercase font-bold">Contract Duration</span>
                      <span className="text-base font-bold text-emerald-900">{selectedContract.contract_duration_days} Days</span>
                    </div>
                    <div className="text-right">
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Processed At</span>
                      <span className="text-xs text-slate-600 font-mono">{new Date(selectedContract.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="border-t border-slate-100 pt-4 flex justify-end">
              <button
                onClick={() => setSelectedContract(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-semibold text-xs transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
