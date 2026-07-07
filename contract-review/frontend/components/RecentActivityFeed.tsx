'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiGet } from '@/lib/api';
import { logger } from '@/lib/logger';
import LoadingSpinner from './LoadingSpinner';

interface Contract {
  id: string;
  created_at: string;
  contract_type: string;
  risk_level: string;
  filename: string;
}

export default function RecentActivityFeed() {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRecentContracts();
  }, []);

  const fetchRecentContracts = async () => {
    try {
      const data = await apiGet<{ contracts: Contract[] }>('/api/admin/recent-contracts');
      setContracts(data.contracts || []);
    } catch (err) {
      logger.error('Error fetching recent contracts:', err);
      setError('Failed to load recent activity');
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'high':
        return 'text-red-600';
      case 'medium':
        return 'text-yellow-600';
      case 'low':
        return 'text-green-600';
      default:
        return 'text-gray-600';
    }
  };

  const getContractTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      vendor: 'Vendor',
      customer: 'Customer',
      employment: 'Employment',
      dpa: 'DPA',
      general: 'General',
      other: 'Other'
    };
    return labels[type] || type;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) {
      return `${diffMins} minutes ago`;
    } else if (diffMins < 1440) {
      const hours = Math.floor(diffMins / 60);
      return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else {
      const days = Math.floor(diffMins / 1440);
      return `${days} day${days > 1 ? 's' : ''} ago`;
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <LoadingSpinner size="md" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 text-red-600">
        {error}
      </div>
    );
  }

  if (contracts.length === 0) {
    return (
      <div className="text-center py-8 text-muted">
        No recent contract activity
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {contracts.map((contract) => (
        <Link
          key={contract.id}
          href={`/admin/contracts/${contract.id}`}
          className="block p-4 border border-border rounded-lg hover:bg-hover transition-colors"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-primary truncate">
                  {contract.filename}
                </span>
                <span className="text-xs text-muted">·</span>
                <span className="text-xs text-muted">
                  {getContractTypeLabel(contract.contract_type)}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3 ml-4">
              <span className={`text-xs font-medium ${getRiskColor(contract.risk_level)}`}>
                {contract.risk_level?.toUpperCase()} RISK
              </span>
              <span className="text-xs text-muted whitespace-nowrap">
                {formatDate(contract.created_at)}
              </span>
            </div>
          </div>
        </Link>
      ))}
    </div>
  );
}
