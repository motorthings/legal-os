'use client';

import { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import LoadingSpinner from './LoadingSpinner';
import { apiGet } from '@/lib/api';
import { logger } from '@/lib/logger';

interface TrendData {
  date: string;
  vendor: number;
  customer: number;
  employment: number;
  dpa: number;
  general: number;
  total: number;
}

interface ActiveUsersData {
  last_7_days: number;
  last_30_days: number;
  total_users: number;
}

export default function UsageAnalytics() {
  const [trends, setTrends] = useState<TrendData[]>([]);
  const [activeUsers, setActiveUsers] = useState<ActiveUsersData | null>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'trends' | 'activity'>('trends');

  useEffect(() => {
    fetchAnalytics();
  }, [days]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      // Fetch usage trends
      const trendsData = await apiGet<{ trends?: TrendData[] }>(`/api/admin/analytics/usage-trends?days=${days}`);
      logger.debug('📊 Usage Trends Response:', trendsData);
      setTrends(trendsData?.trends || []);

      // Fetch active users
      const activeUsersData = await apiGet<{ active_users?: ActiveUsersData }>('/api/admin/analytics/active-users');
      logger.debug('👥 Active Users Response:', activeUsersData);
      setActiveUsers(activeUsersData?.active_users || null);
    } catch (error) {
      logger.error('❌ Error fetching analytics:', error);
      // Set empty data on error to prevent crashes
      setTrends([]);
      setActiveUsers(null);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // Show helpful message if no data available
  // Check for meaningful data, not just empty arrays/objects
  const hasTrends = trends.length > 0 && trends.some(t => t.total > 0);
  const hasActiveUsers = activeUsers !== null && activeUsers.total_users > 0;
  const hasData = hasTrends || hasActiveUsers;

  logger.debug('📈 Data Check:', { hasTrends, hasActiveUsers, hasData, trendsLength: trends.length, activeUsers });

  if (!hasData) {
    return (
      <div className="card p-8 text-center">
        <div className="text-muted mb-4">
          <svg className="w-16 h-16 mx-auto mb-4 text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="text-lg font-semibold text-primary mb-2">No Analytics Data Available</h3>
          <p className="text-sm text-secondary mb-4">
            Analytics data will appear here once contracts start being analyzed.
          </p>
          <p className="text-xs text-muted">
            Contract trends will show the volume of each contract type over time.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Active Users Stats */}
      {activeUsers && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card p-4">
            <div className="text-sm text-secondary mb-1">Active (7 Days)</div>
            <div className="stat-number text-2xl">{activeUsers.last_7_days}</div>
            <div className="text-xs text-secondary mt-1">
              {activeUsers.total_users > 0
                ? `${((activeUsers.last_7_days / activeUsers.total_users) * 100).toFixed(1)}% of total`
                : '0% of total'}
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-secondary mb-1">Active (30 Days)</div>
            <div className="stat-number text-2xl">{activeUsers.last_30_days}</div>
            <div className="text-xs text-secondary mt-1">
              {activeUsers.total_users > 0
                ? `${((activeUsers.last_30_days / activeUsers.total_users) * 100).toFixed(1)}% of total`
                : '0% of total'}
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-secondary mb-1">Total Users</div>
            <div className="stat-number text-2xl">{activeUsers.total_users}</div>
            <div className="text-xs text-secondary mt-1">All registered users</div>
          </div>
        </div>
      )}

      {/* Time Range Selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-secondary">Time Range:</span>
        <button
          onClick={() => setDays(7)}
          className={`px-3 py-1 text-sm rounded ${days === 7 ? 'bg-primary text-white' : 'bg-surface text-primary hover:bg-surface-hover'}`}
        >
          7 Days
        </button>
        <button
          onClick={() => setDays(30)}
          className={`px-3 py-1 text-sm rounded ${days === 30 ? 'bg-primary text-white' : 'bg-surface text-primary hover:bg-surface-hover'}`}
        >
          30 Days
        </button>
        <button
          onClick={() => setDays(90)}
          className={`px-3 py-1 text-sm rounded ${days === 90 ? 'bg-primary text-white' : 'bg-surface text-primary hover:bg-surface-hover'}`}
        >
          90 Days
        </button>
      </div>

      {/* Tab Selector */}
      <div className="flex border-b border-border">
        <button
          onClick={() => setActiveTab('trends')}
          className={`px-4 py-2 text-sm font-medium border-b-2 ${
            activeTab === 'trends'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-primary'
          }`}
        >
          Usage Trends
        </button>
        <button
          onClick={() => setActiveTab('activity')}
          className={`px-4 py-2 text-sm font-medium border-b-2 ${
            activeTab === 'activity'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-primary'
          }`}
        >
          Activity Breakdown
        </button>
      </div>

      {/* Charts */}
      <div className="card p-6">
        {activeTab === 'trends' ? (
          <div>
            <h3 className="text-lg font-semibold text-primary mb-4">Usage Trends Over Time</h3>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatDate}
                  stroke="#888"
                />
                <YAxis stroke="#888" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                  labelStyle={{ color: '#fff' }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="vendor"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  name="Vendor/Supplier"
                />
                <Line
                  type="monotone"
                  dataKey="customer"
                  stroke="#10b981"
                  strokeWidth={2}
                  name="Customer"
                />
                <Line
                  type="monotone"
                  dataKey="employment"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  name="Employment/HR"
                />
                <Line
                  type="monotone"
                  dataKey="dpa"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  name="DPA"
                />
                <Line
                  type="monotone"
                  dataKey="general"
                  stroke="#6b7280"
                  strokeWidth={2}
                  name="General/Other"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div>
            <h3 className="text-lg font-semibold text-primary mb-4">Activity Breakdown</h3>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatDate}
                  stroke="#888"
                />
                <YAxis stroke="#888" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1a1a1a', border: '1px solid #333' }}
                  labelStyle={{ color: '#fff' }}
                />
                <Legend />
                <Bar dataKey="vendor" fill="#3b82f6" name="Vendor/Supplier" />
                <Bar dataKey="customer" fill="#10b981" name="Customer" />
                <Bar dataKey="employment" fill="#f59e0b" name="Employment/HR" />
                <Bar dataKey="dpa" fill="#8b5cf6" name="DPA" />
                <Bar dataKey="general" fill="#6b7280" name="General/Other" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Summary Stats - Contract Type Totals */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="card p-4">
          <div className="text-sm text-secondary mb-1">Vendor/Supplier</div>
          <div className="stat-number text-xl">
            {trends.reduce((sum, day) => sum + day.vendor, 0)}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-secondary mb-1">Customer</div>
          <div className="stat-number text-xl">
            {trends.reduce((sum, day) => sum + day.customer, 0)}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-secondary mb-1">Employment/HR</div>
          <div className="stat-number text-xl">
            {trends.reduce((sum, day) => sum + day.employment, 0)}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-secondary mb-1">DPA</div>
          <div className="stat-number text-xl">
            {trends.reduce((sum, day) => sum + day.dpa, 0)}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm text-secondary mb-1">General/Other</div>
          <div className="stat-number text-xl">
            {trends.reduce((sum, day) => sum + day.general, 0)}
          </div>
        </div>
      </div>
    </div>
  );
}
