'use client';

import { useEffect, useState, useCallback } from 'react';
import { apiGet, APIError } from '@/lib/api';
import { logger } from '@/lib/logger';

interface TrendDataPoint {
  week: string;
  count: number;
}

interface IdeationVelocityData {
  user_id: string;
  time_period: string;
  drafts_initiated: number;
  avg_per_week: number;
  trend_data: TrendDataPoint[];
}

interface IdeationVelocityCardProps {
  timePeriod?: 'week' | 'month' | 'all_time';
  userId?: string;  // Optional: for admins to view specific user's data
}

export default function IdeationVelocityCard({
  timePeriod = 'month',
  userId
}: IdeationVelocityCardProps) {
  const [data, setData] = useState<IdeationVelocityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIdeationVelocity = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Build query parameters
      const params = new URLSearchParams({ time_period: timePeriod });
      if (userId) {
        params.append('user_id', userId);
      }

      const result = await apiGet<IdeationVelocityData>(`/api/kpis/ideation-velocity?${params.toString()}`);
      logger.debug('⚡ Ideation Velocity Response:', result);
      setData(result);
    } catch (err) {
      logger.error('❌ Ideation Velocity Error:', err);
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : 'An error occurred');
      }
    } finally {
      setLoading(false);
    }
  }, [timePeriod, userId]);

  useEffect(() => {
    let mounted = true;

    const loadData = async () => {
      if (mounted) {
        await fetchIdeationVelocity();
      }
    };

    loadData();

    return () => {
      mounted = false;
    };
  }, [fetchIdeationVelocity]);

  const handleRetry = () => {
    fetchIdeationVelocity();
  };

  const getStatusColor = (avgPerWeek: number): string => {
    if (avgPerWeek >= 3) return 'text-green-600';
    if (avgPerWeek >= 2) return 'text-yellow-600';
    return 'text-orange-600';
  };

  const getStatusText = (avgPerWeek: number): string => {
    if (avgPerWeek >= 3) return 'Excellent';
    if (avgPerWeek >= 2) return 'Good';
    return 'Needs Improvement';
  };

  const getStatusIcon = (avgPerWeek: number) => {
    if (avgPerWeek >= 3) {
      return (
        <svg
          className="w-5 h-5 text-green-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          role="img"
          aria-label="Success indicator"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    }
    if (avgPerWeek >= 2) {
      return (
        <svg
          className="w-5 h-5 text-yellow-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          role="img"
          aria-label="Warning indicator"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      );
    }
    return (
      <svg
        className="w-5 h-5 text-orange-600"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        role="img"
        aria-label="Needs attention indicator"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    );
  };

  if (loading) {
    return (
      <div className="bg-card rounded-lg shadow-sm border border-default p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-8 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card rounded-lg shadow-sm border border-default p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <svg
                className="w-5 h-5 icon-primary"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                role="img"
                aria-label="Ideation velocity icon"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Ideation Velocity</h3>
            </div>
            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Strategic drafts initiated per week</p>
          </div>
        </div>

        <div className="text-sm mb-3" style={{ color: 'var(--color-text-secondary)' }}>
          Unable to load ideation velocity data. This might be because no conversations have been created yet.
        </div>
        <button
          onClick={handleRetry}
          className="text-sm text-primary-600 hover:text-primary-700 font-medium transition-colors"
          aria-label="Retry loading ideation velocity data"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  // Show helpful message if no drafts have been initiated yet
  if (data.drafts_initiated === 0) {
    return (
      <div className="bg-card rounded-lg shadow-sm border border-default p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <svg
                className="w-5 h-5 icon-primary"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                role="img"
                aria-label="Ideation velocity icon"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Ideation Velocity</h3>
            </div>
            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Strategic drafts initiated per week</p>
          </div>
        </div>

        <div className="text-3xl font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>
          0.0
          <span className="text-sm font-normal ml-2" style={{ color: 'var(--color-text-secondary)' }}>drafts/week</span>
        </div>

        <div className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)' }}>
          No strategic drafts initiated yet in {data.time_period === 'all_time' ? 'all time' : `the past ${data.time_period}`}.
        </div>

        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-900">
            <strong>Getting Started:</strong> Start conversations with strategic keywords like "draft", "plan", "strategy", "framework", or "report" to track your ideation velocity.
          </p>
        </div>

        <div className="mt-4 pt-4 border-t border-default">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted">Goal: ≥ 2 drafts/week</span>
            <span className="text-orange-600">Not yet tracking</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-lg shadow-sm border border-default p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <svg
              className="w-5 h-5 icon-primary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              role="img"
              aria-label="Ideation velocity icon"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Ideation Velocity</h3>
          </div>
          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Strategic drafts initiated per week</p>
        </div>

        <div className="flex items-center gap-1">
          {getStatusIcon(data.avg_per_week)}
        </div>
      </div>

      {/* Main Metric */}
      <div className="mb-4">
        <div className="text-3xl font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>
          {data.avg_per_week.toFixed(1)}
          <span className="text-sm font-normal ml-2" style={{ color: 'var(--color-text-secondary)' }}>drafts/week</span>
        </div>
        <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          {data.drafts_initiated} total drafts in {data.time_period === 'all_time' ? 'all time' : `past ${data.time_period}`}
        </div>
      </div>

      {/* Trend Visualization */}
      {data.trend_data && data.trend_data.length > 0 && (
        <div className="border-t border-default pt-4">
          <div className="text-xs font-semibold text-secondary mb-2">Recent Trend (Last 8 Weeks)</div>
          <div className="bg-gray-50 p-2 rounded-lg">
            {/* Count labels */}
            <div className="flex gap-1.5 mb-1">
              {data.trend_data.slice(-8).map((point, idx) => (
                <div key={idx} className="flex-1 text-center">
                  <div className="text-[10px] font-semibold text-primary h-3">
                    {point.count > 0 ? point.count : ''}
                  </div>
                </div>
              ))}
            </div>
            {/* Bars */}
            <div className="flex items-end gap-1.5 h-20 mb-1" role="img" aria-label="Trend chart showing drafts over time">
              {data.trend_data.slice(-8).map((point, idx) => {
                const maxCount = Math.max(...data.trend_data.map(p => p.count));
                const height = maxCount > 0 ? Math.min(100, Math.max(0, (point.count / maxCount) * 100)) : 0;
                const displayHeight = point.count > 0 ? Math.max(height, 10) : 2;

                // Convert week format "2025-W46" to date
                const getDateFromWeek = (weekStr: string) => {
                  const [year, week] = weekStr.split('-W');
                  if (!year || !week) return weekStr;
                  // Simple approximation: week N starts on Jan 1 + (N-1)*7 days
                  const date = new Date(parseInt(year), 0, 1 + (parseInt(week) - 1) * 7);
                  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                };

                const dateLabel = getDateFromWeek(point.week);

                return (
                  <div
                    key={idx}
                    className="flex-1 bg-blue-400 hover:bg-blue-500 rounded-t transition-all duration-200 cursor-pointer relative group"
                    style={{ height: `${displayHeight}%` }}
                    title={`${dateLabel}: ${point.count} drafts`}
                    role="presentation"
                  >
                    <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                      {dateLabel}: {point.count} {point.count === 1 ? 'draft' : 'drafts'}
                    </div>
                  </div>
                );
              })}
            </div>
            {/* Date Labels */}
            <div className="flex gap-1.5">
              {data.trend_data.slice(-8).map((point, idx) => {
                const getDateFromWeek = (weekStr: string) => {
                  const [year, week] = weekStr.split('-W');
                  if (!year || !week) return weekStr;
                  const date = new Date(parseInt(year), 0, 1 + (parseInt(week) - 1) * 7);
                  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                };

                return (
                  <div key={idx} className="flex-1 text-center">
                    <div className="text-[10px] text-muted truncate" title={point.week}>
                      {getDateFromWeek(point.week)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Goal Indicator */}
      <div className="mt-4 pt-4 border-t border-default">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted">Goal: ≥ 2 drafts/week</span>
          <span className={getStatusColor(data.avg_per_week)}>
            {getStatusText(data.avg_per_week)}
          </span>
        </div>
        {/* Performance Messages in Boxes */}
        {data.avg_per_week >= 3 && (
          <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-xs text-green-900">
              <strong>✓ Excellent velocity!</strong> Consistently using AI as a force multiplier for strategic work.
              This level of engagement demonstrates effective integration of AI-assisted ideation into regular workflows.
            </p>
          </div>
        )}
        {data.avg_per_week >= 2 && data.avg_per_week < 3 && (
          <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-xs text-yellow-900">
              <strong>Good pace!</strong> Meeting the goal for regular AI-assisted ideation.
              Continue this pattern to maintain consistent strategic output and knowledge application.
            </p>
          </div>
        )}
        {data.avg_per_week < 2 && (
          <div className="mt-3 p-3 bg-orange-50 border border-orange-200 rounded-lg">
            <p className="text-xs text-orange-900">
              <strong>Below target.</strong> Increasing conversation frequency will improve ideation velocity.
              Consider dedicating time for AI-assisted strategic planning and drafting sessions.
            </p>
          </div>
        )}

        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-900">
            <strong>What this measures:</strong> This metric tracks how often users initiate strategic work using the AI assistant,
            indicating force multiplier effect and knowledge application. Higher velocity shows active engagement in high-value work.
            Goal: ≥ 2 drafts per week demonstrates consistent AI-assisted ideation patterns aligned with the Bradbury Impact Loop methodology.
          </p>
        </div>
      </div>
    </div>
  );
}
