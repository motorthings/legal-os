'use client';

import { useState, useEffect } from 'react';
import { apiGet } from '@/lib/api';
import { logger } from '@/lib/logger';
import LoadingSpinner from './LoadingSpinner';

interface RiskDistribution {
  high: number;
  medium: number;
  low: number;
  total: number;
}

interface Props {
  contractType?: string;
}

export default function RiskDetectionSummaryCard({ contractType = 'all' }: Props) {
  const [data, setData] = useState<RiskDistribution | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [contractType]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiGet<RiskDistribution>(
        `/api/admin/analytics/risk-distribution?contract_type=${contractType}`
      );
      
      setData(response);
    } catch (err) {
      logger.error('Error fetching risk distribution:', err);
      setError('Unable to load risk detection data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card p-4">
        <h3 className="text-base font-semibold text-primary mb-3">Risk Detection Summary</h3>
        <div className="flex justify-center py-8">
          <LoadingSpinner size="md" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card p-4">
        <h3 className="text-base font-semibold text-primary mb-3">Risk Detection Summary</h3>
        <div className="text-center py-8">
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

  // Calculate percentages
  const highPercent = data.total > 0 ? (data.high / data.total) * 100 : 0;
  const mediumPercent = data.total > 0 ? (data.medium / data.total) * 100 : 0;
  const lowPercent = data.total > 0 ? (data.low / data.total) * 100 : 0;

  // Create pie chart segments
  const createPieSegment = (percentage: number, startAngle: number, color: string) => {
    const angle = (percentage / 100) * 360;
    const endAngle = startAngle + angle;

    // Convert to radians
    const startRad = (startAngle - 90) * (Math.PI / 180);
    const endRad = (endAngle - 90) * (Math.PI / 180);

    // Circle parameters
    const cx = 100;
    const cy = 100;
    const radius = 80;

    // Calculate path points
    const x1 = cx + radius * Math.cos(startRad);
    const y1 = cy + radius * Math.sin(startRad);
    const x2 = cx + radius * Math.cos(endRad);
    const y2 = cy + radius * Math.sin(endRad);

    // Large arc flag
    const largeArc = angle > 180 ? 1 : 0;

    // Create SVG path
    return {
      path: `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`,
      color,
      percentage,
      endAngle
    };
  };

  // Build pie segments
  const segments = [];
  let currentAngle = 0;

  if (highPercent > 0) {
    segments.push({ ...createPieSegment(highPercent, currentAngle, '#dc2626'), label: 'High', count: data.high });
    currentAngle += (highPercent / 100) * 360;
  }
  if (mediumPercent > 0) {
    segments.push({ ...createPieSegment(mediumPercent, currentAngle, '#d97706'), label: 'Medium', count: data.medium });
    currentAngle += (mediumPercent / 100) * 360;
  }
  if (lowPercent > 0) {
    segments.push({ ...createPieSegment(lowPercent, currentAngle, '#16a34a'), label: 'Low', count: data.low });
  }

  return (
    <div className="card p-4 h-full">
      <h3 className="text-base font-semibold text-primary mb-3">Risk Detection Summary</h3>

      <div className="space-y-4">
        {/* Pie Chart */}
        <div className="flex flex-col items-center">
          <svg viewBox="0 0 200 200" className="w-full max-w-[280px] h-auto">
            {segments.length > 0 ? (
              segments.map((segment, index) => (
                <g key={index}>
                  <path
                    d={segment.path}
                    fill={segment.color}
                    className="hover:opacity-80 transition-opacity cursor-pointer"
                  >
                    <title>{`${segment.label} Risk: ${segment.count} (${segment.percentage.toFixed(1)}%)`}</title>
                  </path>
                </g>
              ))
            ) : (
              <circle cx="100" cy="100" r="80" fill="#e5e7eb" />
            )}
            {/* Center circle for donut effect */}
            <circle cx="100" cy="100" r="45" fill="white" />
            <text x="100" y="95" textAnchor="middle" className="text-2xl font-bold fill-primary">
              {data.total}
            </text>
            <text x="100" y="110" textAnchor="middle" className="text-xs fill-muted">
              Contracts
            </text>
          </svg>
        </div>

        {/* Legend */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-red-600"></div>
              <span className="text-primary font-medium">High Risk</span>
            </div>
            <span className="text-muted">{data.high} ({highPercent.toFixed(1)}%)</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-yellow-600"></div>
              <span className="text-primary font-medium">Medium Risk</span>
            </div>
            <span className="text-muted">{data.medium} ({mediumPercent.toFixed(1)}%)</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-green-600"></div>
              <span className="text-primary font-medium">Low Risk</span>
            </div>
            <span className="text-muted">{data.low} ({lowPercent.toFixed(1)}%)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
