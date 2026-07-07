'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { apiGet, apiPost, apiPut, apiDelete } from '@/lib/api';
import ConfirmModal from '@/components/ConfirmModal';
import toast from 'react-hot-toast';
import AcceptableValuesInput, { STANDARD_TEMPLATES } from './components/AcceptableValuesInput';
import AcceptableValuesDisplay from './components/AcceptableValuesDisplay';

interface LegalStandard {
  id: string;
  category: string;
  term_name: string;
  description: string;
  contract_type: 'vendor' | 'customer' | 'employment' | 'dpa' | 'general' | 'all';
  violation_severity: 'red_flag' | 'yellow_flag' | 'info';
  acceptable_values: Record<string, any>;
  recommendation: string;
  is_active: boolean;
  client_id?: string;
  created_at: string;
  updated_at: string;
}

type StandardFormData = Omit<LegalStandard, 'id' | 'created_at' | 'updated_at'>;

export default function LegalStandardsPage() {
  const [standards, setStandards] = useState<LegalStandard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [contractTypeFilter, setContractTypeFilter] = useState<string>('all_types');
  const [severityFilter, setSeverityFilter] = useState<string>('all_severities');
  const [activeFilter, setActiveFilter] = useState<string>('all_status');
  const [sortBy, setSortBy] = useState<keyof LegalStandard>('violation_severity');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [showForm, setShowForm] = useState(false);
  const [editingStandard, setEditingStandard] = useState<LegalStandard | null>(null);
  const [formData, setFormData] = useState<StandardFormData>({
    category: '',
    term_name: '',
    description: '',
    contract_type: 'all',
    violation_severity: 'yellow_flag',
    acceptable_values: {},
    recommendation: '',
    is_active: true,
  });

  // Confirm modal
  const [confirmModal, setConfirmModal] = useState<{
    open: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
  }>({
    open: false,
    title: '',
    message: '',
    onConfirm: () => {}
  });

  useEffect(() => {
    fetchStandards();
  }, []);

  const fetchStandards = async () => {
    try {
      setLoading(true);
      const data = await apiGet<{ standards: LegalStandard[] }>('/api/legal-standards');
      setStandards(data.standards || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      toast.error('Failed to load legal standards');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (editingStandard) {
        await apiPut(`/api/legal-standards/${editingStandard.id}`, formData);
        toast.success('Legal standard updated successfully');
      } else {
        await apiPost('/api/legal-standards', formData);
        toast.success('Legal standard created successfully');
      }

      // Reset form and refresh list
      resetForm();
      fetchStandards();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save standard');
    }
  };

  const handleEdit = (standard: LegalStandard) => {
    setEditingStandard(standard);
    setFormData({
      category: standard.category,
      term_name: standard.term_name,
      description: standard.description,
      contract_type: standard.contract_type,
      violation_severity: standard.violation_severity,
      acceptable_values: standard.acceptable_values,
      recommendation: standard.recommendation,
      is_active: standard.is_active,
      client_id: standard.client_id,
    });
    setShowForm(true);
  };

  const handleDelete = (standard: LegalStandard) => {
    setConfirmModal({
      open: true,
      title: 'Delete Legal Standard',
      message: `Are you sure you want to delete "${standard.term_name}"? This action cannot be undone.`,
      onConfirm: async () => {
        try {
          await apiDelete(`/api/legal-standards/${standard.id}`);
          toast.success('Legal standard deleted successfully');
          fetchStandards();
        } catch (err) {
          toast.error(err instanceof Error ? err.message : 'Failed to delete standard');
        }
      }
    });
  };

  const handleToggleActive = async (standard: LegalStandard) => {
    try {
      await apiPut(`/api/legal-standards/${standard.id}`, {
        ...standard,
        is_active: !standard.is_active
      });
      toast.success(`Standard ${!standard.is_active ? 'activated' : 'deactivated'}`);
      fetchStandards();
    } catch (err) {
      toast.error('Failed to update standard status');
    }
  };

  const resetForm = () => {
    setFormData({
      category: '',
      term_name: '',
      description: '',
      contract_type: 'all',
      violation_severity: 'yellow_flag',
      acceptable_values: {},
      recommendation: '',
      is_active: true,
    });
    setEditingStandard(null);
    setShowForm(false);
  };

  const filteredStandards = standards
    .filter(standard => {
      // Search filter
      const matchesSearch = standard.term_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        standard.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
        standard.description.toLowerCase().includes(searchTerm.toLowerCase());

      // Contract type filter
      const matchesContractType = contractTypeFilter === 'all_types' ||
        standard.contract_type === contractTypeFilter;

      // Severity filter
      const matchesSeverity = severityFilter === 'all_severities' ||
        standard.violation_severity === severityFilter;

      // Active status filter
      const matchesActive = activeFilter === 'all_status' ||
        (activeFilter === 'active' && standard.is_active) ||
        (activeFilter === 'inactive' && !standard.is_active);

      return matchesSearch && matchesContractType && matchesSeverity && matchesActive;
    })
    .sort((a, b) => {
      // Primary sort
      let comparison = 0;
      const aVal = a[sortBy];
      const bVal = b[sortBy];

      // For severity, use custom ordering: red_flag > yellow_flag > info
      if (sortBy === 'violation_severity') {
        const severityOrder = { 'red_flag': 3, 'yellow_flag': 2, 'info': 1 };
        comparison = (severityOrder[aVal as keyof typeof severityOrder] || 0) -
                    (severityOrder[bVal as keyof typeof severityOrder] || 0);
      } else if (typeof aVal === 'string' && typeof bVal === 'string') {
        comparison = aVal.localeCompare(bVal);
      } else if (typeof aVal === 'boolean' && typeof bVal === 'boolean') {
        comparison = aVal === bVal ? 0 : aVal ? -1 : 1;
      } else if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal;
      }

      const primarySort = sortOrder === 'asc' ? comparison : -comparison;

      // Secondary sort by created_at (newest first) when sorting by severity
      if (primarySort === 0 && sortBy === 'violation_severity') {
        const aDate = new Date(a.created_at).getTime();
        const bDate = new Date(b.created_at).getTime();
        return bDate - aDate; // Newest first
      }

      return primarySort;
    });

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse">Loading legal standards...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="heading-1 mb-2">
          Legal Standards Management
        </h1>
        <p className="text-muted">
          Configure legal compliance standards for automated contract analysis
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="alert alert-error mb-6">
          <p>{error}</p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="card p-3">
          <div className="stat-label mb-0.5">
            Total Standards
          </div>
          <div className="stat-number">
            {standards.length}
          </div>
        </div>
        <div className="card p-3">
          <div className="stat-label mb-0.5">
            Active
          </div>
          <div className="stat-number text-green-600">
            {standards.filter(s => s.is_active).length}
          </div>
        </div>
        <div className="card p-3">
          <div className="stat-label mb-0.5">
            Red Flags
          </div>
          <div className="stat-number text-red-600">
            {standards.filter(s => s.violation_severity === 'red_flag').length}
          </div>
        </div>
        <div className="card p-3">
          <div className="stat-label mb-0.5">
            Contract Types
          </div>
          <div className="stat-number">
            {new Set(standards.map(s => s.contract_type)).size}
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="space-y-4 mb-6">
        <div className="flex gap-4">
          <input
            type="text"
            placeholder="Search by term name, category, or description..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-field flex-1"
          />
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap gap-4 items-center justify-between">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2">
              <label className="text-sm text-secondary">Contract Type:</label>
              <select
                value={contractTypeFilter}
                onChange={(e) => setContractTypeFilter(e.target.value)}
                className="input-field w-40"
              >
                <option value="all_types">All Types</option>
                <option value="vendor">Vendor</option>
                <option value="customer">Customer</option>
                <option value="employment">Employment</option>
                <option value="dpa">DPA</option>
                <option value="general">General</option>
                <option value="all">All Contracts</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm text-secondary">Severity:</label>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="input-field w-36"
              >
                <option value="all_severities">All Severities</option>
                <option value="red_flag">Red Flag</option>
                <option value="yellow_flag">Yellow Flag</option>
                <option value="info">Info</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm text-secondary">Status:</label>
              <select
                value={activeFilter}
                onChange={(e) => setActiveFilter(e.target.value)}
                className="input-field w-32"
              >
                <option value="all_status">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm text-secondary">Sort By:</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as keyof LegalStandard)}
                className="input-field w-36"
              >
                <option value="category">Category</option>
                <option value="term_name">Term Name</option>
                <option value="violation_severity">Severity</option>
                <option value="contract_type">Contract Type</option>
                <option value="created_at">Date Created</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm text-secondary">Order:</label>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                className="input-field w-32"
              >
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
              </select>
            </div>

            {/* Clear Filters */}
            {(searchTerm || contractTypeFilter !== 'all_types' || severityFilter !== 'all_severities' ||
              activeFilter !== 'all_status' || sortBy !== 'violation_severity' || sortOrder !== 'desc') && (
              <button
                onClick={() => {
                  setSearchTerm('');
                  setContractTypeFilter('all_types');
                  setSeverityFilter('all_severities');
                  setActiveFilter('all_status');
                  setSortBy('violation_severity');
                  setSortOrder('desc');
                }}
                className="text-sm text-secondary hover:text-primary transition-colors"
              >
                Clear Filters
              </button>
            )}
          </div>

          {/* Add Standard Button */}
          <button
            onClick={() => {
              resetForm();
              setShowForm(!showForm);
            }}
            className="btn-primary"
          >
            {showForm ? 'Cancel' : '+ Add Standard'}
          </button>
        </div>
      </div>

      {/* Add/Edit Form */}
      {showForm && (
        <div className="card mb-6 p-6">
          <h3 className="heading-3 mb-4">
            {editingStandard ? 'Edit Legal Standard' : 'Add New Legal Standard'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">
                  Category *
                </label>
                <input
                  type="text"
                  required
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="input-field"
                  placeholder="e.g., Liability, Payment Terms"
                />
              </div>
              <div>
                <label className="label">
                  Term Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.term_name}
                  onChange={(e) => setFormData({ ...formData, term_name: e.target.value })}
                  className="input-field"
                  placeholder="e.g., Liability Cap"
                />
              </div>
            </div>

            <div>
              <label className="label">
                Description *
              </label>
              <textarea
                required
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="input-field"
                rows={3}
                placeholder="Describe what this standard checks for..."
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="label">
                  Contract Type *
                </label>
                <select
                  value={formData.contract_type}
                  onChange={(e) => setFormData({ ...formData, contract_type: e.target.value as any })}
                  className="input-field"
                >
                  <option value="all">All Contracts</option>
                  <option value="vendor">Vendor</option>
                  <option value="customer">Customer</option>
                  <option value="employment">Employment</option>
                  <option value="dpa">DPA</option>
                  <option value="general">General</option>
                </select>
              </div>
              <div>
                <label className="label">
                  Violation Severity *
                </label>
                <select
                  value={formData.violation_severity}
                  onChange={(e) => setFormData({ ...formData, violation_severity: e.target.value as any })}
                  className="input-field"
                >
                  <option value="info">Info</option>
                  <option value="yellow_flag">Yellow Flag</option>
                  <option value="red_flag">Red Flag</option>
                </select>
              </div>
              <div>
                <label className="label">
                  Status
                </label>
                <select
                  value={formData.is_active ? 'active' : 'inactive'}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.value === 'active' })}
                  className="input-field"
                >
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>
            </div>

            <div>
              <AcceptableValuesInput
                value={formData.acceptable_values}
                onChange={(newValue) => setFormData({ ...formData, acceptable_values: newValue })}
                category={formData.category}
                termName={formData.term_name}
                onTemplateSelect={(template) => {
                  if (template) {
                    // Auto-populate category, term name, and recommendation if empty
                    setFormData({
                      ...formData,
                      category: formData.category || template.category,
                      term_name: formData.term_name || template.name,
                      description: formData.description || template.description,
                      recommendation: formData.recommendation || template.recommendationTemplate || '',
                    });
                  }
                }}
              />
            </div>

            <div>
              <label className="label">
                Recommendation *
              </label>
              <textarea
                required
                value={formData.recommendation}
                onChange={(e) => setFormData({ ...formData, recommendation: e.target.value })}
                className="input-field"
                rows={2}
                placeholder="What should be done if this standard is violated?"
              />
            </div>

            <div className="flex gap-3">
              <button
                type="submit"
                className="btn-primary"
              >
                {editingStandard ? 'Update Standard' : 'Create Standard'}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Standards Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead style={{ backgroundColor: 'var(--color-bg-muted)' }} className="border-b border-default">
              <tr>
                <th className="px-2 py-2 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                  Category
                </th>
                <th className="px-2 py-2 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                  Term
                </th>
                <th className="px-2 py-2 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                  Criteria
                </th>
                <th className="px-2 py-2 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                  Type
                </th>
                <th className="px-2 py-2 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                  Severity
                </th>
                <th className="px-2 py-2 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                  Status
                </th>
                <th className="px-2 py-2 text-left text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-default">
              {filteredStandards.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-muted">
                    {searchTerm || contractTypeFilter !== 'all_types' ?
                      'No standards found matching your filters' :
                      'No legal standards yet'}
                  </td>
                </tr>
              ) : (
                filteredStandards.map((standard) => (
                  <tr key={standard.id} className="hover:bg-hover transition-colors">
                    <td className="px-2 py-2 whitespace-nowrap">
                      <div className="text-sm font-medium text-primary">
                        {standard.category}
                      </div>
                    </td>
                    <td className="px-2 py-2">
                      <div className="text-sm text-primary font-medium">
                        {standard.term_name}
                      </div>
                      <div className="text-xs text-muted line-clamp-1 mt-0.5">
                        {standard.description}
                      </div>
                    </td>
                    <td className="px-2 py-2">
                      <AcceptableValuesDisplay
                        value={standard.acceptable_values}
                        compact={true}
                      />
                    </td>
                    <td className="px-2 py-2 whitespace-nowrap">
                      <span className="badge-secondary text-xs">
                        {standard.contract_type}
                      </span>
                    </td>
                    <td className="px-2 py-2 whitespace-nowrap">
                      <span
                        className="px-2 py-0.5 rounded-full text-xs font-medium inline-flex items-center"
                        style={{
                          backgroundColor:
                            standard.violation_severity === 'red_flag' ? '#ef4444' :
                            standard.violation_severity === 'yellow_flag' ? '#f59e0b' :
                            '#e5e5e9',
                          color:
                            standard.violation_severity === 'red_flag' ? 'white' :
                            standard.violation_severity === 'yellow_flag' ? 'white' :
                            '#6b7280'
                        }}
                      >
                        {standard.violation_severity === 'red_flag' ? 'Red' :
                         standard.violation_severity === 'yellow_flag' ? 'Yellow' :
                         'Info'}
                      </span>
                    </td>
                    <td className="px-2 py-2 whitespace-nowrap">
                      <button
                        onClick={() => handleToggleActive(standard)}
                        className={`text-xs ${standard.is_active ? 'badge-success' : 'badge-muted'}`}
                      >
                        {standard.is_active ? 'Active' : 'Inactive'}
                      </button>
                    </td>
                    <td className="px-2 py-2 whitespace-nowrap text-sm">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEdit(standard)}
                          className="link font-medium text-xs"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(standard)}
                          className="text-red-600 hover:text-red-700 font-medium text-xs"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Results Count */}
      <div className="mt-4 text-sm text-muted">
        Showing {filteredStandards.length} of {standards.length} standards
      </div>

      {/* Confirm Modal */}
      <ConfirmModal
        open={confirmModal.open}
        title={confirmModal.title}
        message={confirmModal.message}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal({ ...confirmModal, open: false })}
      />
    </div>
  );
}
