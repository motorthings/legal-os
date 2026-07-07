'use client';

import { useState, useEffect } from 'react';
import { apiGet } from '@/lib/api';
import { logger } from '@/lib/logger';
import LoadingSpinner from './LoadingSpinner';

interface TrendData {
  date: string;
  count: number;
  avg_risk_score: number;
}

interface Props {
  contractType?: string;
}

export default function ContractAnalysisTrendPanel({ contractType = 'all' }: Props) {
  const [data, setData] = useState<TrendData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [contractType]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch all available data (up to 30 days) with daily granularity
      const response = await apiGet<{ trends: TrendData[] }>(
        `/api/admin/analytics/contract-trends?contract_type=${contractType}&days=30`
      );

      setData(response.trends || []);
    } catch (err) {
      logger.error('Error fetching contract trends:', err);
      setError('Unable to load trend data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-primary mb-4">Contract Analysis Trends (30 Days)</h3>
        <div className="flex justify-center py-12">
          <LoadingSpinner size="md" />
        </div>
      </div>
    );
  }

  if (error || data.length === 0) {
    return (
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-primary mb-4">Contract Analysis Trends (30 Days)</h3>
        <div className="text-center py-12">
          <p className="text-muted mb-4">{error || 'No trend data available'}</p>
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

  // Calculate time range for dynamic display
  // Parse dates flexibly to handle different formats
  const parseFlexibleDate = (dateStr: string): Date => {
    if (dateStr.includes('W')) {
      // ISO week format: YYYY-WXX
      const [year, week] = dateStr.split('-W');
      return new Date(parseInt(year), 0, 1 + (parseInt(week) - 1) * 7);
    }
    return new Date(dateStr);
  };

  const firstDate = data.length > 0 ? parseFlexibleDate(data[0].date) : new Date();
  const lastDate = data.length > 0 ? parseFlexibleDate(data[data.length - 1].date) : new Date();

  // Calculate difference in hours first for more precision
  const hoursDiff = Math.max(0, (lastDate.getTime() - firstDate.getTime()) / (1000 * 60 * 60));
  const daysDiff = Math.max(0, Math.ceil(hoursDiff / 24));

  // Determine time unit and format based on range
  let timeRangeLabel = '';
  if (data.length === 1) {
    timeRangeLabel = 'Single Point';
  } else if (hoursDiff < 1) {
    timeRangeLabel = 'Less than 1 Hour';
  } else if (hoursDiff <= 24) {
    // Hourly data for same day or less than 24 hours
    const hours = Math.ceil(hoursDiff);
    timeRangeLabel = hours === 1 ? '1 Hour' : `${hours} Hours`;
  } else if (daysDiff === 1) {
    timeRangeLabel = '1 Day';
  } else if (daysDiff <= 7) {
    timeRangeLabel = `${daysDiff} Days`;
  } else if (daysDiff <= 30) {
    const weeks = Math.ceil(daysDiff / 7);
    timeRangeLabel = weeks === 1 ? '1 Week' : `${weeks} Weeks`;
  } else {
    const months = Math.ceil(daysDiff / 30);
    timeRangeLabel = months === 1 ? '1 Month' : `${months} Months`;
  }

  // Calculate scales
  const maxCount = Math.max(...data.map(d => d.count), 1);
  const maxRisk = 100;

  // Chart dimensions
  const chartWidth = 800;
  const chartHeight = 300;
  const padding = { top: 20, right: 60, bottom: 60, left: 60 };
  const plotWidth = chartWidth - padding.left - padding.right;
  const plotHeight = chartHeight - padding.top - padding.bottom;

  // Calculate points for volume line
  // Handle edge case: if only 1 data point, center it; otherwise distribute evenly
  const volumePoints = data.map((item, index) => {
    let x;
    if (data.length === 1) {
      x = padding.left + plotWidth / 2; // Center single point
    } else {
      x = padding.left + (index / (data.length - 1)) * plotWidth;
    }
    const y = padding.top + plotHeight - (item.count / maxCount) * plotHeight;
    return { x, y, count: item.count };
  });

  // Calculate points for risk score line
  const riskPoints = data.map((item, index) => {
    let x;
    if (data.length === 1) {
      x = padding.left + plotWidth / 2; // Center single point
    } else {
      x = padding.left + (index / (data.length - 1)) * plotWidth;
    }
    const y = padding.top + plotHeight - (item.avg_risk_score / maxRisk) * plotHeight;
    return { x, y, score: item.avg_risk_score };
  });

  // Create path strings
  const volumePath = volumePoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const riskPath = riskPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

  // Y-axis ticks for volume (left axis)
  const volumeTicks = [0, Math.floor(maxCount * 0.25), Math.floor(maxCount * 0.5), Math.floor(maxCount * 0.75), maxCount];

  // Y-axis ticks for risk score (right axis)
  const riskTicks = [0, 25, 50, 75, 100];

  // X-axis ticks (show every 5th day or smart intervals)
  const xTickInterval = Math.ceil(data.length / 6);

  return (
    <div className="card p-6 h-full flex flex-col">
      <h3 className="text-lg font-semibold text-primary mb-6">Contract Analysis Trends ({timeRangeLabel})</h3>

      {/* Line Chart */}
      <div className="overflow-x-auto flex-1 flex items-center">
        <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full h-auto">
          {/* Grid lines */}
          {volumeTicks.map((tick, i) => {
            const y = padding.top + plotHeight - (tick / maxCount) * plotHeight;
            return (
              <line
                key={`grid-${i}`}
                x1={padding.left}
                y1={y}
                x2={chartWidth - padding.right}
                y2={y}
                stroke="#e5e7eb"
                strokeWidth="1"
                strokeDasharray="4,4"
              />
            );
          })}

          {/* X-axis */}
          <line
            x1={padding.left}
            y1={chartHeight - padding.bottom}
            x2={chartWidth - padding.right}
            y2={chartHeight - padding.bottom}
            stroke="#374151"
            strokeWidth="2"
          />

          {/* Y-axis (left - Volume) */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={chartHeight - padding.bottom}
            stroke="#374151"
            strokeWidth="2"
          />

          {/* Y-axis (right - Risk Score) */}
          <line
            x1={chartWidth - padding.right}
            y1={padding.top}
            x2={chartWidth - padding.right}
            y2={chartHeight - padding.bottom}
            stroke="#374151"
            strokeWidth="2"
          />

          {/* Y-axis labels (left - Volume) */}
          {volumeTicks.map((tick, i) => {
            const y = padding.top + plotHeight - (tick / maxCount) * plotHeight;
            return (
              <text
                key={`vol-tick-${i}`}
                x={padding.left - 10}
                y={y + 4}
                textAnchor="end"
                className="text-xs fill-gray-600"
              >
                {tick}
              </text>
            );
          })}

          {/* Y-axis labels (right - Risk Score) */}
          {riskTicks.map((tick, i) => {
            const y = padding.top + plotHeight - (tick / maxRisk) * plotHeight;
            return (
              <text
                key={`risk-tick-${i}`}
                x={chartWidth - padding.right + 10}
                y={y + 4}
                textAnchor="start"
                className="text-xs fill-gray-600"
              >
                {tick}
              </text>
            );
          })}

          {/* X-axis labels (dates) */}
          {data.map((item, index) => {
            if (index % xTickInterval !== 0 && index !== data.length - 1) return null;
            let x;
            if (data.length === 1) {
              x = padding.left + plotWidth / 2;
            } else {
              x = padding.left + (index / (data.length - 1)) * plotWidth;
            }

            // Format date based on time range - keep labels concise
            // Handle various date formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, YYYY-WXX
            let dateLabel = '';
            let itemDate: Date;

            // Parse different date formats
            if (item.date.includes('W')) {
              // ISO week format: YYYY-WXX
              const [year, week] = item.date.split('-W');
              // Approximate date from week number
              const firstDay = new Date(parseInt(year), 0, 1 + (parseInt(week) - 1) * 7);
              itemDate = firstDay;
              const month = firstDay.toLocaleDateString('en-US', { month: 'short' });
              dateLabel = `${month} W${week}`;
            } else {
              // Standard date format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
              itemDate = new Date(item.date);

              // Check if date is valid
              if (isNaN(itemDate.getTime())) {
                dateLabel = item.date.substring(0, 10); // Fallback to raw string
              } else {
                // Check if this is hourly data (has time component)
                const hasTime = item.date.includes(':');

                if (hasTime && daysDiff <= 1) {
                  // For hourly data within 24 hours, show time
                  const hour = itemDate.getHours();
                  const ampm = hour >= 12 ? 'p' : 'a';
                  const displayHour = hour % 12 || 12;
                  dateLabel = `${displayHour}${ampm}`;
                } else if (daysDiff <= 30) {
                  // For daily data up to 30 days, show M/D
                  const month = itemDate.getMonth() + 1;
                  const day = itemDate.getDate();
                  dateLabel = `${month}/${day}`;
                } else {
                  // For longer ranges, show Mon'YY
                  const month = itemDate.toLocaleDateString('en-US', { month: 'short' });
                  const year = itemDate.getFullYear().toString().slice(-2);
                  dateLabel = `${month}'${year}`;
                }
              }
            }

            return (
              <text
                key={`date-${index}`}
                x={x}
                y={chartHeight - padding.bottom + 20}
                textAnchor="middle"
                className="text-xs fill-gray-600"
                style={{ fontSize: '11px' }}
              >
                {dateLabel}
              </text>
            );
          })}

          {/* Axis titles */}
          <text
            x={padding.left / 2}
            y={chartHeight / 2}
            textAnchor="middle"
            transform={`rotate(-90, ${padding.left / 2}, ${chartHeight / 2})`}
            className="text-sm font-medium fill-blue-600"
          >
            Contract Volume
          </text>

          <text
            x={chartWidth - padding.right / 2}
            y={chartHeight / 2}
            textAnchor="middle"
            transform={`rotate(90, ${chartWidth - padding.right / 2}, ${chartHeight / 2})`}
            className="text-sm font-medium fill-orange-600"
          >
            Avg Risk Score
          </text>

          {/* X-axis title (Days) */}
          <text
            x={chartWidth / 2}
            y={chartHeight - 5}
            textAnchor="middle"
            className="text-sm font-medium fill-gray-600"
          >
            Days
          </text>

          {/* Volume line */}
          <>
            <path
              d={volumePath}
              fill="none"
              stroke="#2563eb"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {/* Volume data points */}
            {volumePoints.map((point, i) => (
              <circle
                key={`vol-point-${i}`}
                cx={point.x}
                cy={point.y}
                r="4"
                fill="#2563eb"
                className="hover:r-6 transition-all cursor-pointer"
              >
                <title>{`${data[i].date}: ${point.count} contracts`}</title>
              </circle>
            ))}
          </>

          {/* Risk score line */}
          <>
            <path
              d={riskPath}
              fill="none"
              stroke="#ea580c"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {/* Risk data points */}
            {riskPoints.map((point, i) => (
              <circle
                key={`risk-point-${i}`}
                cx={point.x}
                cy={point.y}
                r="4"
                fill="#ea580c"
                className="hover:r-6 transition-all cursor-pointer"
              >
                <title>{`${data[i].date}: ${point.score.toFixed(1)} risk score`}</title>
              </circle>
            ))}
          </>
        </svg>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 mt-4">
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-blue-600"></div>
          <span className="text-xs text-gray-600">Contract Volume</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-orange-600"></div>
          <span className="text-xs text-gray-600">Average Risk Score</span>
        </div>
      </div>
    </div>
  );
}
