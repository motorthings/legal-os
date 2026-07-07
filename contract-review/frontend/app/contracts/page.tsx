'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import LoadingSpinner from '@/components/LoadingSpinner';
import { apiGet } from '@/lib/api';
import { logger } from '@/lib/logger';

interface ContractStats {
  total_contracts: number;
  high_risk_count: number;
  high_risk_percent: number;
  medium_risk_count: number;
  medium_risk_percent: number;
  low_risk_count: number;
  low_risk_percent: number;
  pending_review_count: number;
  human_review_required_count: number;
  avg_risk_score: number;
  avg_confidence_score: number;
}

interface Contract {
  id: string;
  document_id: string;
  contract_type: string;
  parties: string[];
  effective_date: string;
  total_value: number;
  overall_risk_level: 'high' | 'medium' | 'low';
  risk_score: number;
  human_review_required: boolean;
  review_status: 'pending' | 'approved' | 'approved_with_conditions' | 'negotiation_required' | 'rejected';
  executive_summary: string;
  created_at: string;
  documents: {
    filename: string;
    counterparty_name: string;
    uploaded_at: string;
  };
}

export default function ContractsDashboard() {
  const [stats, setStats] = useState<ContractStats | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'high-priority' | 'kpis' | 'analytics'>('overview');
  const [riskFilter, setRiskFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [reviewStatusFilter, setReviewStatusFilter] = useState<string>('all');
  const [reprocessing, setReprocessing] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [contractTypeFilter, setContractTypeFilter] = useState<string>('all');

  useEffect(() => {
    fetchDashboardData();
  }, [riskFilter, reviewStatusFilter, activeTab]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);

      // Fetch stats
      const statsData = await apiGet<{ success: boolean; stats: ContractStats }>('/api/contracts/dashboard/stats');
      setStats(statsData.stats);

      // Fetch contracts list based on active tab
      let queryParams = new URLSearchParams();

      if (activeTab === 'high-priority') {
        queryParams.append('human_review_required', 'true');
      } else if (riskFilter !== 'all') {
        queryParams.append('risk_level', riskFilter);
      }

      if (reviewStatusFilter !== 'all') {
        queryParams.append('review_status', reviewStatusFilter);
      }

      const contractsData = await apiGet<{ success: boolean; contracts: Contract[] }>(
        `/api/contracts?${queryParams.toString()}`
      );
      setContracts(contractsData.contracts || []);

    } catch (error) {
      logger.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReprocess = async (documentId: string) => {
    if (!confirm('Are you sure you want to reprocess this contract? This will delete the current analysis and create a new one.')) {
      return;
    }

    try {
      setReprocessing(prev => new Set(prev).add(documentId));

      const response = await fetch(`/api/contracts/${documentId}/reprocess`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to reprocess contract');
      }

      // Refresh the data
      await fetchDashboardData();

      logger.info('Contract reprocessing started:', documentId);
    } catch (error) {
      logger.error('Error reprocessing contract:', error);
      alert('Failed to reprocess contract. Please try again.');
    } finally {
      setReprocessing(prev => {
        const next = new Set(prev);
        next.delete(documentId);
        return next;
      });
    }
  };

  const getRiskBadgeColor = (level: string) => {
    switch (level) {
      case 'high': return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'low': return 'bg-green-500/20 text-green-400 border-green-500/30';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  const getReviewStatusBadge = (status: string) => {
    const statusMap = {
      'pending': { label: 'Pending Review', color: 'bg-gray-500/20 text-gray-400' },
      'approved': { label: 'Approved', color: 'bg-green-500/20 text-green-400' },
      'approved_with_conditions': { label: 'Approved with Conditions', color: 'bg-yellow-500/20 text-yellow-400' },
      'negotiation_required': { label: 'Needs Negotiation', color: 'bg-orange-500/20 text-orange-400' },
      'rejected': { label: 'Rejected', color: 'bg-red-500/20 text-red-400' }
    };
    const badge = statusMap[status as keyof typeof statusMap] || statusMap.pending;
    return <span className={`px-2 py-1 rounded text-xs font-medium ${badge.color}`}>{badge.label}</span>;
  };

  // Filter contracts based on search query and contract type
  const filteredContracts = contracts.filter(contract => {
    // Search filter
    const matchesSearch = !searchQuery ||
      contract.documents.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (contract.documents.counterparty_name?.toLowerCase() || '').includes(searchQuery.toLowerCase()) ||
      (contract.contract_type?.toLowerCase() || '').includes(searchQuery.toLowerCase());

    // Contract type filter
    const matchesType = contractTypeFilter === 'all' ||
      (contract.contract_type?.toLowerCase() || '').includes(contractTypeFilter.toLowerCase());

    return matchesSearch && matchesType;
  });

  return (
    <div className="w-full">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-primary">
            Contract Review Dashboard
          </h1>
          <p className="text-sm text-secondary mt-1">
            AI-powered contract analysis with risk assessment and triage
          </p>
        </div>
        <Link
          href="/contracts/upload"
          className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary-600 transition-colors"
        >
          Upload Contract
        </Link>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-border mb-8">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'overview'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-primary'
          }`}
        >
          All Contracts
        </button>
        <button
          onClick={() => setActiveTab('high-priority')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors relative ${
            activeTab === 'high-priority'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-primary'
          }`}
        >
          High Priority
          {stats && stats.human_review_required_count > 0 && (
            <span className="ml-2 px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
              {stats.human_review_required_count}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('kpis')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'kpis'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-primary'
          }`}
        >
          KPIs
        </button>
        <button
          onClick={() => setActiveTab('analytics')}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'analytics'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-primary'
          }`}
        >
          Analytics
        </button>
      </div>

      {activeTab === 'overview' || activeTab === 'high-priority' ? (
        <div className="space-y-8">
          {/* Quick Stats */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-primary mb-6">Contract Portfolio</h2>
            {loading || !stats ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner size="md" />
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-6 md:gap-8">
                <div className="text-center">
                  <div className="text-4xl font-bold text-primary mb-2">{stats.total_contracts}</div>
                  <div className="text-base font-medium text-secondary">Total Contracts</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl font-bold text-red-400 mb-2">{stats.high_risk_count}</div>
                  <div className="text-base font-medium text-secondary">High Risk</div>
                  <div className="text-xs text-secondary mt-1">{stats.high_risk_percent}%</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl font-bold text-yellow-400 mb-2">{stats.medium_risk_count}</div>
                  <div className="text-base font-medium text-secondary">Medium Risk</div>
                  <div className="text-xs text-secondary mt-1">{stats.medium_risk_percent}%</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl font-bold text-green-400 mb-2">{stats.low_risk_count}</div>
                  <div className="text-base font-medium text-secondary">Low Risk</div>
                  <div className="text-xs text-secondary mt-1">{stats.low_risk_percent}%</div>
                </div>
                <div className="text-center">
                  <div className="text-4xl font-bold text-blue-400 mb-2">{stats.avg_confidence_score.toFixed(1)}%</div>
                  <div className="text-base font-medium text-secondary">Avg Confidence</div>
                  <div className="text-xs text-secondary mt-1">Analysis Quality</div>
                </div>
              </div>
            )}
          </div>

          {/* Search and Filters */}
          {activeTab === 'overview' && (
            <div className="card p-4 space-y-4">
              {/* Search Bar */}
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <svg className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <input
                    type="text"
                    placeholder="Search by filename, counterparty, or contract type..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-border rounded-md text-sm bg-background text-primary placeholder-secondary focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-secondary hover:text-primary"
                      title="Clear search"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>

              {/* Filter Controls */}
              <div className="flex flex-wrap gap-4 items-center">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium text-secondary">Contract Type:</label>
                  <select
                    value={contractTypeFilter}
                    onChange={(e) => setContractTypeFilter(e.target.value)}
                    className="px-3 py-1.5 border border-border rounded-md text-sm bg-background"
                  >
                    <option value="all">All Types</option>
                    <option value="nda">NDA</option>
                    <option value="dpa">DPA</option>
                    <option value="sow">SOW</option>
                    <option value="msa">MSA</option>
                    <option value="sla">SLA</option>
                    <option value="employment">Employment</option>
                    <option value="general">General</option>
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium text-secondary">Risk Level:</label>
                  <select
                    value={riskFilter}
                    onChange={(e) => setRiskFilter(e.target.value as any)}
                    className="px-3 py-1.5 border border-border rounded-md text-sm bg-background"
                  >
                    <option value="all">All Levels</option>
                    <option value="high">High Risk Only</option>
                    <option value="medium">Medium Risk Only</option>
                    <option value="low">Low Risk Only</option>
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium text-secondary">Status:</label>
                  <select
                    value={reviewStatusFilter}
                    onChange={(e) => setReviewStatusFilter(e.target.value)}
                    className="px-3 py-1.5 border border-border rounded-md text-sm bg-background"
                  >
                    <option value="all">All Statuses</option>
                    <option value="pending">Pending Review</option>
                    <option value="approved">Approved</option>
                    <option value="negotiation_required">Needs Negotiation</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>

                {/* Results Count */}
                {(searchQuery || contractTypeFilter !== 'all') && (
                  <div className="ml-auto text-sm text-secondary">
                    Showing {filteredContracts.length} of {contracts.length} contracts
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Contracts List */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-primary mb-4">
              {activeTab === 'high-priority' ? 'Contracts Requiring Review' : 'Contract List'}
            </h2>

            {loading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner size="md" />
              </div>
            ) : contracts.length === 0 ? (
              <div className="text-center py-12 text-secondary">
                <p className="text-lg mb-2">No contracts found</p>
                <p className="text-sm">Upload a contract to get started with AI-powered analysis</p>
              </div>
            ) : filteredContracts.length === 0 ? (
              <div className="text-center py-12 text-secondary">
                <svg className="w-16 h-16 mx-auto mb-4 text-secondary opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <p className="text-lg mb-2">No contracts match your search</p>
                <p className="text-sm mb-4">Try adjusting your search or filter criteria</p>
                <button
                  onClick={() => {
                    setSearchQuery('');
                    setContractTypeFilter('all');
                  }}
                  className="text-sm text-primary hover:underline"
                >
                  Clear all filters
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4 text-sm font-medium text-secondary">Contract</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-secondary">Counterparty</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-secondary">Risk Level</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-secondary">Status</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-secondary">Issues</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-secondary">Uploaded</th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-secondary">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredContracts.map((contract) => (
                      <tr key={contract.id} className="border-b border-border hover:bg-muted/50 transition-colors">
                        <td className="py-3 px-4">
                          <div className="flex flex-col">
                            <span className="font-medium text-primary">{contract.documents.filename}</span>
                            {contract.contract_type && (
                              <span className="text-xs text-secondary">{contract.contract_type}</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-sm text-primary">
                          {contract.documents.counterparty_name || '-'}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getRiskBadgeColor(contract.overall_risk_level)}`}>
                            {contract.overall_risk_level.toUpperCase()} ({contract.risk_score ?? 'N/A'})
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          {getReviewStatusBadge(contract.review_status)}
                        </td>
                        <td className="py-3 px-4">
                          {contract.human_review_required && (
                            <span className="flex items-center gap-1 text-orange-400 text-xs">
                              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                              </svg>
                              Human Review
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-sm text-secondary">
                          {new Date(contract.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-3">
                            <Link
                              href={`/contracts/${contract.document_id}`}
                              className="text-sm text-primary hover:text-primary-600 font-medium"
                            >
                              View Details →
                            </Link>
                            <button
                              onClick={() => handleReprocess(contract.document_id)}
                              disabled={reprocessing.has(contract.document_id)}
                              className="text-secondary hover:text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Reprocess contract"
                            >
                              {reprocessing.has(contract.document_id) ? (
                                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                              ) : (
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                              )}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : activeTab === 'kpis' ? (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-primary mb-4">Contract Review KPIs</h2>
          <p className="text-secondary">KPI metrics coming soon - tracking review efficiency, risk trends, and decision quality.</p>
        </div>
      ) : (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-primary mb-4">Contract Analytics</h2>
          <p className="text-secondary">Analytics dashboard coming soon - visualizing risk distribution, common issues, and portfolio health.</p>
        </div>
      )}
    </div>
  );
}
