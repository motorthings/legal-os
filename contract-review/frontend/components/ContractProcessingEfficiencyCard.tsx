'use client';

import { useState, useEffect } from 'react';
import { apiGet } from '@/lib/api';
import { logger } from '@/lib/logger';
import LoadingSpinner from './LoadingSpinner';

interface ProcessingEfficiency {
  avg_processing_time_minutes: number;
  total_contracts: number;
  contracts_by_type: {
    [key: string]: {
      count: number;
      avg_time_minutes: number;
    };
  };
}

interface Props {
  contractType?: string;
}

export default function ContractProcessingEfficiencyCard({ contractType = 'all' }: Props) {
  const [data, setData] = useState<ProcessingEfficiency | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [contractType]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiGet<ProcessingEfficiency>(
        `/api/admin/analytics/processing-efficiency?contract_type=${contractType}`
      );
      
      setData(response);
    } catch (err) {
      logger.error('Error fetching processing efficiency:', err);
      setError('Unable to load processing efficiency data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-primary mb-4">Contract Processing Efficiency</h3>
        <div className="flex justify-center py-12">
          <LoadingSpinner size="md" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-primary mb-4">Contract Processing Efficiency</h3>
        <div className="text-center py-12">
          <p className="text-muted mb-4">{error || 'No data available'}</p>
          <button
            onClick={fetchData}
            className="text-sm text-primary hover:underline"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-primary mb-4">Contract Processing Efficiency</h3>
      
      <div className="space-y-6">
        {/* Overall Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-4 bg-primary-50 rounded-lg">
            <div className="text-3xl font-bold text-primary">
              {data.avg_processing_time_minutes.toFixed(1)}
            </div>
            <div className="text-sm text-muted mt-1">Avg Time (min)</div>
          </div>
          <div className="text-center p-4 bg-primary-50 rounded-lg">
            <div className="text-3xl font-bold text-primary">
              {data.total_contracts}
            </div>
            <div className="text-sm text-muted mt-1">Total Contracts</div>
          </div>
        </div>

        {/* By Contract Type */}
        {contractType === 'all' && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-primary">By Contract Type</h4>
            {Object.entries(data.contracts_by_type || {}).map(([type, stats]) => (
              <div key={type} className="flex items-center justify-between py-2 border-b border-border">
                <span className="text-sm text-primary capitalize">{type}</span>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-muted">{stats.count} contracts</span>
                  <span className="text-sm font-medium text-primary">
                    {stats.avg_time_minutes.toFixed(1)} min
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
