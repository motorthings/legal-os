'use client';

import { useEffect, useState, useCallback, ReactElement } from 'react';
import { apiGet, APIError } from '@/lib/api';

interface CorrectionLoopData {
  user_id: string;
  avg_turns_to_completion: number;
  total_completed_conversations: number;
  distribution: Record<string, number>;
  goal_status: 'met' | 'close' | 'needs_improvement' | 'no_data';
}

interface CorrectionLoopCardProps {
  userId?: string;  // Optional: for admins to view specific user's data
}

export default function CorrectionLoopCard({ userId }: CorrectionLoopCardProps = {}) {
  const [data, setData] = useState<CorrectionLoopData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCorrectionLoop = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Build query parameters
      const params = new URLSearchParams();
      if (userId) {
        params.append('user_id', userId);
      }

      const queryString = params.toString();
      const url = queryString ? `/api/kpis/correction-loop?${queryString}` : '/api/kpis/correction-loop';

      const result = await apiGet<CorrectionLoopData>(url);
      setData(result);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : 'An error occurred');
      }
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    let mounted = true;

    const loadData = async () => {
      if (mounted) {
        await fetchCorrectionLoop();
      }
    };

    loadData();

    return () => {
      mounted = false;
    };
  }, [fetchCorrectionLoop]);

  const handleRetry = () => {
    fetchCorrectionLoop();
  };

  const getStatusColor = (status: string): string => {
    if (status === 'met') return 'text-green-600';
    if (status === 'close') return 'text-yellow-600';
    if (status === 'needs_improvement') return 'text-orange-600';
    return 'text-gray-600';
  };

  const getStatusText = (status: string): string => {
    if (status === 'met') return 'Excellent';
    if (status === 'close') return 'Good';
    if (status === 'needs_improvement') return 'Needs Improvement';
    return 'No Data';
  };

  const getStatusIcon = (status: string): ReactElement => {
    if (status === 'met') {
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
    if (status === 'close') {
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
                aria-label="Correction loop icon"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Correction Loop Efficiency</h3>
            </div>
            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Average turns to usable output</p>
          </div>
        </div>

        <div className="text-sm mb-3" style={{ color: 'var(--color-text-secondary)' }}>
          Unable to load correction loop data. This might be because no conversations have been created yet.
        </div>
        <button
          onClick={handleRetry}
          className="text-sm text-primary-600 hover:text-primary-700 font-medium transition-colors"
          aria-label="Retry loading correction loop data"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!data || data.goal_status === 'no_data') {
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
                aria-label="Correction loop icon"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Correction Loop Efficiency</h3>
            </div>
            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Average turns to usable output</p>
          </div>
        </div>

        <div className="text-3xl font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>
          0.0
          <span className="text-sm font-normal ml-2" style={{ color: 'var(--color-text-secondary)' }}>avg turns</span>
        </div>

        <div className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)' }}>
          No conversations analyzed yet.
        </div>

        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-900">
            <strong>How it works:</strong> This metric tracks how many back-and-forth exchanges are needed before getting usable output. Lower is better - it means your system instructions and prompting are effective.
          </p>
        </div>

        <div className="mt-4 pt-4 border-t border-default">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted">Goal: &lt; 2 turns average</span>
            <span className="text-gray-600">Not yet tracking</span>
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
              aria-label="Correction loop icon"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <h3 className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>Correction Loop Efficiency</h3>
          </div>
          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Average turns to usable output</p>
        </div>

        <div className="flex items-center gap-1">
          {getStatusIcon(data.goal_status)}
        </div>
      </div>

      {/* Main Metric */}
      <div className="mb-4">
        <div className="text-3xl font-bold mb-1" style={{ color: 'var(--color-text-primary)' }}>
          {data.avg_turns_to_completion.toFixed(1)}
          <span className="text-sm font-normal ml-2" style={{ color: 'var(--color-text-secondary)' }}>avg turns</span>
        </div>
        <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          {data.total_completed_conversations} conversations analyzed
        </div>
      </div>

      {/* Distribution */}
      {Object.keys(data.distribution).length > 0 && (
        <div className="border-t border-default pt-4 mb-4">
          <div className="text-xs font-semibold text-secondary mb-2">Distribution</div>
          <div className="space-y-2">
            {(() => {
              // Sort distribution by numeric turn count (1, 2, 3, 4+)
              const sortedEntries = Object.entries(data.distribution).sort((a, b) => {
                const aNum = parseInt(a[0].split('_')[0]);
                const bNum = parseInt(b[0].split('_')[0]);
                return aNum - bNum;
              });

              // Group 4+ turns together
              const grouped: Array<[string, number]> = [];
              let fourPlusCount = 0;

              sortedEntries.forEach(([key, count]) => {
                const turnNum = parseInt(key.split('_')[0]);
                if (turnNum >= 4) {
                  fourPlusCount += count;
                } else {
                  grouped.push([key, count]);
                }
              });

              if (fourPlusCount > 0) {
                grouped.push(['4+ turns', fourPlusCount]);
              }

              return grouped.map(([turns, count]) => {
                const percentage = data.total_completed_conversations > 0
                  ? Math.min(100, Math.max(0, (count / data.total_completed_conversations) * 100))
                  : 0;

                // Ensure minimum visible width for small percentages
                const displayWidth = percentage < 5 && percentage > 0 ? 5 : percentage;

                return (
                  <div key={turns} className="flex items-center gap-2">
                    <div className="text-xs text-muted w-16 flex-shrink-0">{turns.replace('_', ' ')}</div>
                    <div className="flex-1 bg-gray-200 rounded-full h-3 relative overflow-hidden">
                      <div
                        className="absolute top-0 left-0 h-full bg-blue-500 rounded-full transition-all duration-300"
                        style={{ width: `${displayWidth}%` }}
                        role="progressbar"
                        aria-valuenow={percentage}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label={`${turns}: ${percentage.toFixed(1)}%`}
                      />
                    </div>
                    <div className="text-xs text-muted w-12 text-right flex-shrink-0">{count}</div>
                  </div>
                );
              });
            })()}
          </div>
        </div>
      )}

      {/* Goal Indicator */}
      <div className="pt-4 border-t border-default">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted">Goal: &lt; 2 turns average</span>
          <span className={getStatusColor(data.goal_status)}>
            {getStatusText(data.goal_status)}
          </span>
        </div>

        {/* Detailed Explanations */}
        {data.avg_turns_to_completion < 2 && (
          <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-xs text-green-900">
              <strong>✓ Excellent assistant performance!</strong> The assistant is delivering useable output quickly.
              System instructions are clear, AI functions are well-designed, and the assistant effectively
              understands user intent on the first or second exchange.
            </p>
          </div>
        )}
        {data.avg_turns_to_completion >= 2 && data.avg_turns_to_completion < 3 && (
          <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-xs text-yellow-900">
              <strong>Good assistant performance.</strong> The assistant typically reaches useable output within
              a reasonable number of exchanges. Monitor this metric to ensure it stays below 2 turns on average.
              Consider refining system instructions or function definitions if it trends upward.
            </p>
          </div>
        )}
        {data.avg_turns_to_completion >= 3 && (
          <div className="mt-3 p-3 bg-orange-50 border border-orange-200 rounded-lg">
            <p className="text-xs text-orange-900">
              <strong>Assistant needs improvement.</strong> The assistant requires several exchanges to deliver useable output.
              This suggests system instructions need clarification, AI functions need better definitions,
              or the assistant needs more context/examples to understand user intent. Review high-turn conversations
              to identify failure patterns and improve assistant capabilities.
            </p>
          </div>
        )}

        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-900">
            <strong>What this measures:</strong> This metric evaluates the assistant's ability to deliver
            useable output efficiently. It tracks the average number of user turns (messages) required before
            the assistant produces output that meets the user's needs. Lower numbers indicate the assistant
            is effectively understanding intent and responding appropriately. This measures assistant effectiveness,
            not user performance.
          </p>
        </div>
      </div>
    </div>
  );
}
