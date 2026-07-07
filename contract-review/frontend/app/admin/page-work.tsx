'use client';

import { useState, useEffect } from 'react';
import LoadingSpinner from '@/components/LoadingSpinner';
import ContractAnalysisTrendPanel from '@/components/ContractAnalysisTrendPanel';
import { apiGet } from '@/lib/api';
import { logger } from '@/lib/logger';

interface Stats {
  contractsCompletedWeek: number;
  averageReviewTimeMinutes: number;
  avgConfidenceScore: number;
  contractsWithFeedback: number;
  highRiskCount: number;
  highRiskPercent: number;
  mediumRiskCount: number;
  mediumRiskPercent: number;
  lowRiskCount: number;
  lowRiskPercent: number;
}

interface PerformanceMetric {
  date: string;
  pages_per_minute: number;
  page_count: number;
  processing_time_seconds: number;
  document_id: string;
}

interface PerformanceSummary {
  avg_pages_per_minute: number;
  total_contracts_analyzed: number;
  total_pages_processed: number;
  total_processing_time_seconds: number;
  period_days: number;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats>({
    contractsCompletedWeek: 0,
    averageReviewTimeMinutes: 0,
    avgConfidenceScore: 0,
    contractsWithFeedback: 0,
    highRiskCount: 0,
    highRiskPercent: 0,
    mediumRiskCount: 0,
    mediumRiskPercent: 0,
    lowRiskCount: 0,
    lowRiskPercent: 0
  });
  const [loading, setLoading] = useState(true);
  const [selectedContractType, setSelectedContractType] = useState<string>('all');
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetric[]>([]);
  const [performanceSummary, setPerformanceSummary] = useState<PerformanceSummary | null>(null);
  const [performanceLoading, setPerformanceLoading] = useState(false);

  useEffect(() => {
    fetchStats();
    fetchPerformanceMetrics();
  }, []);

  const fetchStats = async () => {
    try {
      const data = await apiGet<{
        contracts_completed_week: number;
        average_review_time_minutes: number;
        avg_confidence_score: number;
        contracts_with_feedback: number;
        high_risk_count: number;
        high_risk_percent: number;
        medium_risk_count: number;
        medium_risk_percent: number;
        low_risk_count: number;
        low_risk_percent: number;
      }>('/api/admin/contract-stats');

      setStats({
        contractsCompletedWeek: data.contracts_completed_week || 0,
        averageReviewTimeMinutes: data.average_review_time_minutes || 0,
        avgConfidenceScore: data.avg_confidence_score || 0,
        contractsWithFeedback: data.contracts_with_feedback || 0,
        highRiskCount: data.high_risk_count || 0,
        highRiskPercent: data.high_risk_percent || 0,
        mediumRiskCount: data.medium_risk_count || 0,
        mediumRiskPercent: data.medium_risk_percent || 0,
        lowRiskCount: data.low_risk_count || 0,
        lowRiskPercent: data.low_risk_percent || 0
      });
    } catch (error) {
      logger.error('Error fetching contract stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchPerformanceMetrics = async () => {
    try {
      setPerformanceLoading(true);
      const data = await apiGet<{ metrics: PerformanceMetric[]; summary: PerformanceSummary }>('/api/contracts/dashboard/performance?days=30');
      setPerformanceMetrics(data.metrics || []);
      setPerformanceSummary(data.summary);
    } catch (err) {
      logger.error('Error fetching performance metrics:', err);
    } finally {
      setPerformanceLoading(false);
    }
  };


  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-primary">
          Dashboard
        </h1>
      </div>

      <div className="space-y-6">
        {/* Quick Stats */}
        <div className="card p-4">
          {loading ? (
            <div className="flex justify-center py-6">
              <LoadingSpinner size="md" />
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 md:gap-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-primary mb-1">{stats.contractsCompletedWeek}</div>
                <div className="text-sm font-medium text-secondary">Completed Contracts</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-400 mb-1">{Math.round(stats.avgConfidenceScore)}%</div>
                <div className="text-sm font-medium text-secondary">Category Confidence</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-green-500 mb-1">{stats.contractsWithFeedback}</div>
                <div className="text-sm font-medium text-secondary">Team Feedback</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-primary mb-1">{stats.averageReviewTimeMinutes.toFixed(1)}</div>
                <div className="text-sm font-medium text-secondary">Review Time (min)</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-red-500 mb-1">{stats.highRiskCount}</div>
                <div className="text-sm font-medium text-secondary">High Risk ({stats.highRiskPercent.toFixed(0)}%)</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-yellow-500 mb-1">{stats.mediumRiskCount}</div>
                <div className="text-sm font-medium text-secondary">Medium Risk ({stats.mediumRiskPercent.toFixed(0)}%)</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-green-600 mb-1">{stats.lowRiskCount}</div>
                <div className="text-sm font-medium text-secondary">Low Risk ({stats.lowRiskPercent.toFixed(0)}%)</div>
              </div>
            </div>
          )}
        </div>

        {/* Contract Analysis Trends - Full Width */}
        <ContractAnalysisTrendPanel contractType={selectedContractType} />

        {/* Performance Panel - Bottom */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-primary mb-6">Processing Speed Over Time</h2>

          {performanceLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="md" />
            </div>
          ) : performanceMetrics.length === 0 ? (
            <div className="text-center py-12 text-secondary">
              <p className="text-lg mb-2">No performance data yet</p>
              <p className="text-sm">Upload and analyze contracts to start tracking performance metrics</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Bar chart with Y-axis */}
              <div className="flex gap-2">
                {/* Y-axis with label */}
                <div className="flex items-center gap-1">
                  {/* Y-axis label (vertical) - centered on scale */}
                  <div className="h-80 w-6 flex items-center justify-center">
                    <div className="text-sm font-medium text-secondary -rotate-90 whitespace-nowrap">
                      Pages per Minute
                    </div>
                  </div>

                  {/* Y-axis tick marks */}
                  <div className="flex flex-col justify-between h-80 text-xs text-secondary pr-2 border-r border-border">
                    {(() => {
                      const maxPagesPerMin = Math.max(...performanceMetrics.map(m => m.pages_per_minute));
                      const maxScale = Math.ceil(maxPagesPerMin + 0.5); // Add 0.5 then round up to nearest integer
                      const step = maxScale / 5; // Divide into 5 equal intervals for 6 tick marks
                      const ticks = Array.from({ length: 6 }, (_, i) => step * (5 - i));
                      return ticks.map((value, idx) => (
                        <div key={idx} className="flex items-center justify-end">
                          <span className="w-12 text-right">{value.toFixed(1)}</span>
                        </div>
                      ));
                    })()}
                  </div>
                </div>

                {/* Chart area */}
                <div className="flex-1 flex flex-col">
                  {/* Bars container */}
                  <div className="h-80 flex items-end gap-2 border-b border-l border-border relative">
                    {performanceMetrics.map((metric, idx) => {
                      const maxPagesPerMin = Math.max(...performanceMetrics.map(m => m.pages_per_minute));
                      const maxScale = Math.ceil(maxPagesPerMin + 0.5); // Use same scale as Y-axis
                      const minHeight = 20; // Minimum height in pixels for visibility
                      const maxHeight = 300; // Maximum height in pixels (h-80 = 320px, minus some padding)
                      const heightPx = Math.max(minHeight, (metric.pages_per_minute / maxScale) * maxHeight);

                      return (
                        <div
                          key={idx}
                          className="flex-1 bg-primary hover:bg-primary-600 transition-colors rounded-t relative group cursor-pointer flex items-start justify-center pt-2"
                          style={{ height: `${heightPx}px` }}
                        >
                          {/* Value label on bar */}
                          <div className="text-white text-xs font-semibold">
                            {metric.pages_per_minute.toFixed(1)}
                          </div>

                          {/* Hover tooltip with date/time and details */}
                          <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded whitespace-nowrap z-10">
                            <div className="text-gray-400 text-[10px] mb-1">{new Date(metric.date).toLocaleString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                              hour: 'numeric',
                              minute: '2-digit'
                            })}</div>
                            <div className="font-semibold">{metric.pages_per_minute.toFixed(2)} pages/min</div>
                            <div className="text-gray-300">{metric.page_count} pages in {metric.processing_time_seconds.toFixed(0)}s</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Date labels under bars */}
                  <div className="flex gap-2 mt-2">
                    {performanceMetrics.map((metric, idx) => {
                      const date = new Date(metric.date);
                      const month = date.getMonth() + 1;
                      const day = date.getDate();
                      return (
                        <div key={idx} className="flex-1 text-center text-xs text-secondary">
                          {month}/{day}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Legend */}
              <div className="border-t border-border pt-4">
                <div className="text-sm text-secondary">
                  <p className="text-xs">Showing {performanceMetrics.length} contract{performanceMetrics.length !== 1 ? 's' : ''} from the last {performanceSummary?.period_days || 30} days • Hover over bars for details</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
