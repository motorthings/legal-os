'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiPostFormData } from '@/lib/api';
import { logger } from '@/lib/logger';

export default function ContractUploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [contractType, setContractType] = useState('');
  const [counterpartyName, setCounterpartyName] = useState('');
  const [redact, setRedact] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    try {
      setUploading(true);
      setError('');

      const formData = new FormData();
      formData.append('file', file);
      if (contractType) formData.append('contract_type', contractType);
      if (counterpartyName) formData.append('counterparty_name', counterpartyName);
      formData.append('redact', redact.toString());

      const response = await apiPostFormData<{
        success: boolean;
        document_id: string;
        filename: string;
        message: string;
      }>('/api/contracts/upload', formData);

      logger.info('Contract uploaded successfully:', response);

      // Redirect to contracts list with success message
      router.push('/contracts');

    } catch (error) {
      logger.error('Upload error:', error);
      setError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <Link href="/contracts" className="text-sm text-primary hover:underline mb-2 inline-block">
          ← Back to Contracts
        </Link>
        <h1 className="text-3xl font-bold text-primary mb-2">
          Upload Contract for Analysis
        </h1>
        <p className="text-sm text-secondary">
          Upload a contract and our AI will analyze it for risks, extract key terms, and provide recommendations.
        </p>
      </div>

      <div className="card p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-primary mb-2">
              Contract File *
            </label>
            <div className="border-2 border-dashed border-border rounded-lg p-8 text-center hover:border-primary transition-colors">
              <input
                type="file"
                accept=".pdf,.docx,.doc,.txt"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                <div className="space-y-2">
                  <svg className="w-12 h-12 text-secondary mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  {file ? (
                    <div>
                      <p className="text-sm font-medium text-primary">{file.name}</p>
                      <p className="text-xs text-secondary">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-sm font-medium text-primary">Click to upload contract</p>
                      <p className="text-xs text-secondary">PDF, DOCX, DOC, or TXT (max 10MB)</p>
                    </div>
                  )}
                </div>
              </label>
            </div>
          </div>

          {/* Contract Type */}
          <div>
            <label htmlFor="contract-type" className="block text-sm font-medium text-primary mb-2">
              Contract Type
            </label>
            <select
              id="contract-type"
              value={contractType}
              onChange={(e) => setContractType(e.target.value)}
              className="w-full px-4 py-2 border border-border rounded-md bg-background text-primary focus:ring-2 focus:ring-primary focus:outline-none"
            >
              <option value="">Select type (optional)</option>
              <option value="Vendor Agreement">Vendor Agreement</option>
              <option value="SaaS Agreement">SaaS Agreement</option>
              <option value="Professional Services Agreement">Professional Services Agreement</option>
              <option value="Master Service Agreement">Master Service Agreement (MSA)</option>
              <option value="Statement of Work">Statement of Work (SOW)</option>
              <option value="Data Processing Agreement">Data Processing Agreement (DPA)</option>
              <option value="Non-Disclosure Agreement">Non-Disclosure Agreement (NDA)</option>
              <option value="Employment Agreement">Employment Agreement</option>
              <option value="Customer Agreement">Customer Agreement</option>
              <option value="Partnership Agreement">Partnership Agreement</option>
              <option value="Licensing Agreement">Licensing Agreement</option>
              <option value="Other">Other</option>
            </select>
            <p className="text-xs text-secondary mt-1">
              Helps improve analysis accuracy
            </p>
          </div>

          {/* Counterparty Name */}
          <div>
            <label htmlFor="counterparty" className="block text-sm font-medium text-primary mb-2">
              Counterparty Name
            </label>
            <input
              type="text"
              id="counterparty"
              value={counterpartyName}
              onChange={(e) => setCounterpartyName(e.target.value)}
              placeholder="e.g., Acme Corp"
              className="w-full px-4 py-2 border border-border rounded-md bg-background text-primary focus:ring-2 focus:ring-primary focus:outline-none"
            />
            <p className="text-xs text-secondary mt-1">
              The other party to the contract (optional)
            </p>
          </div>

          {/* Redact Confidential Information Toggle */}
          <div className="flex items-center justify-between p-4 border rounded-lg" style={{ borderColor: 'var(--color-border-default)', backgroundColor: 'var(--color-bg-card)' }}>
            <div className="flex-1">
              <label htmlFor="redact-toggle" className="block text-sm font-medium mb-1 cursor-pointer" style={{ color: 'var(--color-text-primary)' }}>
                Redact Confidential Information
              </label>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                id="redact-toggle"
                checked={redact}
                onChange={(e) => setRedact(e.target.checked)}
                className="sr-only peer"
              />
              <div
                className="w-11 h-6 rounded-full peer peer-focus:outline-none peer-focus:ring-4 transition-colors"
                style={{
                  backgroundColor: redact ? 'var(--color-primary)' : '#e5e7eb',
                  boxShadow: redact ? '0 0 0 4px rgba(20, 184, 166, 0.2)' : 'none'
                }}
              >
                <div
                  className="absolute top-[2px] left-[2px] bg-white border border-gray-300 rounded-full h-5 w-5 transition-transform"
                  style={{
                    transform: redact ? 'translateX(20px)' : 'translateX(0)'
                  }}
                ></div>
              </div>
            </label>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-md">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Submit Button */}
          <div className="flex gap-4">
            <button
              type="submit"
              disabled={!file || uploading}
              className="flex-1 px-6 py-3 bg-primary text-white rounded-md hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {uploading ? 'Uploading & Analyzing...' : 'Upload Contract'}
            </button>
            <Link
              href="/contracts"
              className="px-6 py-3 border border-border rounded-md hover:bg-muted transition-colors font-medium text-center"
            >
              Cancel
            </Link>
          </div>
        </form>

        {/* Info Panel */}
        <div className="mt-8 p-4 bg-muted/30 rounded-lg">
          <h3 className="text-sm font-semibold text-primary mb-2">What happens after upload?</h3>
          <ul className="text-xs text-secondary space-y-1">
            <li>• <strong>Automatic Analysis:</strong> AI extracts key terms and assesses risk</li>
            <li>• <strong>Risk Scoring:</strong> Contracts categorized as High, Medium, or Low risk</li>
            <li>• <strong>Human Review Flags:</strong> Complex issues are flagged for expert attention</li>
            <li>• <strong>Triage Dashboard:</strong> View all contracts with prioritized review queue</li>
            <li>• <strong>Decision Tracking:</strong> Document your review decisions and notes</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
