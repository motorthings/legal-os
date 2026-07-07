'use client';

import { useEffect, useState, useCallback } from 'react';
import { apiGet, APIError } from '@/lib/api';

interface TrendDataPoint {
  week: string;
  avg_turns: number;
  conversation_count: number;
}

interface CorrectionLoopData {
  user_id: string;
  avg_turns_to_completion: number;
  total_completed_conversations: number;
  distribution: Record<string, number>;
  goal_status: 'met' | 'close' | 'needs_improvement' | 'no_data';
  trend_data?: TrendDataPoint[];
}

interface CorrectionLoopTrendPanelProps {
  userId?: string;
}

export default function CorrectionLoopTrendPanel({ userId }: CorrectionLoopTrendPanelProps) {
  const [data, setData] = useState<CorrectionLoopData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCorrectionLoop = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

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

  if (loading) {
    return (
      <div className="bg-card rounded-lg shadow-sm border border-default p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !data || !data.trend_data || data.trend_data.length === 0) {
    return null; // Don't show panel if no trend data
  }

  const getDateFromWeek = (weekStr: string) => {
    const [year, week] = weekStr.split('-W');
    if (!year || !week) return weekStr;
    const date = new Date(parseInt(year), 0, 1 + (parseInt(week) - 1) * 7);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

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
              aria-label="Trend chart icon"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
            </svg>
            <h3 className="text-lg font-bold" style={{ color: 'var(--color-text-primary)' }}>Correction Loop Efficiency Over Time</h3>
          </div>
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Track how assistant effectiveness improves as adjustments are made</p>
        </div>
      </div>

      {/* Trend Chart */}
      <div className="bg-gray-50 p-4 rounded-lg">
        {/* Avg turns labels */}
        <div className="flex gap-2 mb-2">
          {data.trend_data.map((point, idx) => (
            <div key={idx} className="flex-1 text-center">
              <div className="text-xs font-semibold text-primary h-4">
                {point.avg_turns > 0 ? point.avg_turns.toFixed(1) : ''}
              </div>
            </div>
          ))}
        </div>

        {/* Bars with Goal Line */}
        <div className="flex items-end gap-2 h-48 mb-2 relative" role="img" aria-label="Correction loop efficiency trend over time">
          {/* Goal line at 2.0 turns */}
          <div
            className="absolute left-0 right-0 border-t-2 border-dashed border-green-500 z-10"
            style={{ bottom: '66.67%' }}
          >
            <span className="absolute -top-5 right-0 text-xs text-green-600 font-semibold bg-card px-1">
              Goal: &lt; 2 turns
            </span>
          </div>

          {data.trend_data.map((point, idx) => {
            const maxTurns = Math.max(...data.trend_data!.map(p => p.avg_turns), 3);
            const height = maxTurns > 0 ? Math.min(100, Math.max(0, (point.avg_turns / maxTurns) * 100)) : 0;
            const displayHeight = point.avg_turns > 0 ? Math.max(height, 10) : 2;

            const dateLabel = getDateFromWeek(point.week);

            // Color based on performance
            let barColor = 'bg-orange-400 hover:bg-orange-500';
            if (point.avg_turns < 2) {
              barColor = 'bg-green-400 hover:bg-green-500';
            } else if (point.avg_turns <= 3) {
              barColor = 'bg-yellow-400 hover:bg-yellow-500';
            }

            return (
              <div
                key={idx}
                className={`flex-1 ${barColor} rounded-t transition-all duration-200 cursor-pointer relative group`}
                style={{ height: `${displayHeight}%` }}
                title={`${dateLabel}: ${point.avg_turns.toFixed(1)} avg turns (${point.conversation_count} conversations)`}
                role="presentation"
              >
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-20">
                  <strong>{dateLabel}</strong><br/>
                  Avg Turns: {point.avg_turns.toFixed(1)}<br/>
                  Conversations: {point.conversation_count}
                </div>
              </div>
            );
          })}
        </div>

        {/* Date Labels */}
        <div className="flex gap-2">
          {data.trend_data.map((point, idx) => (
            <div key={idx} className="flex-1 text-center">
              <div className="text-xs text-muted truncate" title={point.week}>
                {getDateFromWeek(point.week)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Legend and Explanation */}
      <div className="mt-4 pt-4 border-t border-default">
        <div className="flex items-center gap-4 mb-3 text-xs">
          <div className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 bg-green-400 rounded"></span>
            <span className="text-muted">Excellent (&lt;2 turns)</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 bg-yellow-400 rounded"></span>
            <span className="text-muted">Good (2-3 turns)</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 bg-orange-400 rounded"></span>
            <span className="text-muted">Needs Improvement (&gt;3 turns)</span>
          </div>
        </div>

        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-900">
            <strong>What this measures:</strong> This trend shows how the assistant's ability to deliver useable output
            is changing over time. Lower values indicate the assistant is becoming more effective at understanding user
            intent and responding appropriately on the first or second exchange. Monitor this trend to measure the impact
            of system instruction improvements, AI function refinements, and other assistant adjustments.
          </p>
        </div>
      </div>
    </div>
  );
}
