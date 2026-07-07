'use client';

import { useState, useEffect } from 'react';
import { apiGet } from '@/lib/api';
import { logger } from '@/lib/logger';
import LoadingSpinner from './LoadingSpinner';

export default function QuickActionsPanel() {
  const [systemStatus, setSystemStatus] = useState<'healthy' | 'degraded' | 'down'>('healthy');
  const [healthMetrics, setHealthMetrics] = useState({
    supabase: { status: 'checking', responseTime: 0 },
    railway: { status: 'checking', uptime: false },
    vercel: { status: 'checking', build: '' },
    anthropic: { status: 'checking', latency: 0 }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHealthMetrics();
    // Refresh every 60 seconds
    const interval = setInterval(fetchHealthMetrics, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchHealthMetrics = async () => {
    try {
      const response = await apiGet<{ success: boolean; health: any }>('/api/admin/health');
      logger.debug('Health check response:', response);

      if (response.success && response.health) {
        logger.debug('Health data:', response.health);
        setHealthMetrics(response.health);

        // Determine overall system status based on all services
        const { supabase, railway, anthropic } = response.health;

        // Critical services: Supabase and Railway must be up
        if (supabase.status === 'error' || railway.status === 'error') {
          setSystemStatus('down');
        }
        // All services healthy
        else if (
          supabase.status === 'connected' &&
          railway.status === 'running' &&
          (anthropic.status === 'active' || anthropic.status === 'idle')
        ) {
          setSystemStatus('healthy');
        }
        // Some services degraded but system functional
        else {
          setSystemStatus('degraded');
        }
      } else {
        logger.warn('Health check returned unexpected response:', response);
        setSystemStatus('degraded');
      }
    } catch (error) {
      logger.error('Error fetching health metrics:', error);
      logger.error('Full error details:', error);
      // Don't immediately mark as down - could be temporary network issue
      setSystemStatus('degraded');
    } finally {
      setLoading(false);
    }
  };

  // Service status color coding
  const getServiceStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
      case 'running':
      case 'deployed':
      case 'active':
        return 'text-green-400';
      case 'idle':
        return 'text-blue-400';
      case 'error':
      case 'down':
        return 'text-red-400';
      default:
        return 'text-secondary';
    }
  };

  const getResponseTimeColor = (ms: number) => {
    if (ms === 0) return 'text-secondary';
    if (ms <= 100) return 'text-green-400';
    if (ms <= 300) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getLatencyColor = (seconds: number) => {
    if (seconds === 0) return 'text-secondary';
    if (seconds <= 2) return 'text-green-400';
    if (seconds <= 5) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getStatusColor = () => {
    switch (systemStatus) {
      case 'healthy':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'down':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = () => {
    switch (systemStatus) {
      case 'healthy':
        return 'All Operational';
      case 'degraded':
        return 'Degraded Performance';
      case 'down':
        return 'Down';
      default:
        return 'Unknown Status';
    }
  };

  // Format service status with metrics
  const formatSupabaseStatus = () => {
    const status = healthMetrics.supabase?.status || 'checking';
    const responseTime = healthMetrics.supabase?.responseTime || 0;

    if (status === 'error' || status === 'down') {
      return 'Error';
    }

    if (status === 'checking' || responseTime === 0) {
      return 'Checking';
    }

    // Return performance description based on response time
    if (responseTime <= 100) return 'Fast';
    if (responseTime <= 300) return 'Good';
    return 'Slow';
  };

  const formatAnthropicStatus = () => {
    const status = healthMetrics.anthropic?.status || 'checking';
    const latency = healthMetrics.anthropic?.latency || 0;
    if (latency > 0) {
      return `${status.charAt(0).toUpperCase() + status.slice(1)} (${latency.toFixed(1)}s)`;
    }
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  const formatVercelStatus = () => {
    const status = healthMetrics.vercel?.status || 'checking';
    const build = healthMetrics.vercel?.build || '';
    if (build) {
      return `${status.charAt(0).toUpperCase() + status.slice(1)}`;
    }
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  // Determine color based on combined status + metric
  const getSupabaseColor = () => {
    const status = healthMetrics.supabase?.status || 'checking';
    const responseTime = healthMetrics.supabase?.responseTime || 0;

    if (status === 'error' || status === 'down') return 'text-red-400';
    if (status === 'checking') return 'text-secondary';

    // Color based on response time if connected
    if (responseTime === 0) return 'text-green-400';
    if (responseTime <= 100) return 'text-green-400';
    if (responseTime <= 300) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getAnthropicColor = () => {
    const status = healthMetrics.anthropic?.status || 'checking';
    const latency = healthMetrics.anthropic?.latency || 0;

    if (status === 'error' || status === 'down') return 'text-red-400';
    if (status === 'checking') return 'text-secondary';
    if (status === 'idle') return 'text-blue-400';

    // Color based on latency if active
    if (latency === 0) return 'text-green-400';
    if (latency <= 2) return 'text-green-400';
    if (latency <= 5) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getVercelColor = () => {
    const status = healthMetrics.vercel?.status || 'checking';

    if (status === 'error' || status === 'down') return 'text-red-400';
    if (status === 'checking') return 'text-secondary';
    if (status === 'deployed' || status === 'running') return 'text-green-400';

    return 'text-green-400';
  };

  if (loading) {
    return (
      <div className="card p-3">
        <h3 className="text-base font-semibold text-primary mb-3">System Health</h3>
        <div className="flex justify-center py-6">
          <LoadingSpinner size="md" />
        </div>
      </div>
    );
  }

  return (
    <div className="card p-3">
      {/* Header with Overall Status */}
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-2 h-2 rounded-full ${getStatusColor()} animate-pulse`}></div>
        <div>
          <h3 className="text-base font-semibold text-primary">System Health</h3>
          <p className="text-xs text-secondary">{getStatusText()}</p>
        </div>
      </div>

      {/* Service Status Grid */}
      <div className="grid grid-cols-4 gap-4 md:gap-6">
        {/* Supabase (DB) */}
        <div className="text-center">
          <div className={`text-2xl font-bold mb-1 ${getSupabaseColor()}`}>
            {formatSupabaseStatus()}
          </div>
          <div className="text-sm font-medium text-secondary mb-0.5">Supabase</div>
          <div className="text-xs text-muted">DB</div>
        </div>

        {/* Railway (API) */}
        <div className="text-center">
          <div className={`text-2xl font-bold mb-1 capitalize ${getServiceStatusColor(healthMetrics.railway?.status || 'checking')}`}>
            {healthMetrics.railway?.status || 'Checking'}
          </div>
          <div className="text-sm font-medium text-secondary mb-0.5">Railway</div>
          <div className="text-xs text-muted">Backend API</div>
        </div>

        {/* Vercel (Frontend) */}
        <div className="text-center">
          <div className={`text-2xl font-bold mb-1 ${getVercelColor()}`}>
            {formatVercelStatus()}
          </div>
          <div className="text-sm font-medium text-secondary mb-0.5">Vercel</div>
          <div className="text-xs text-muted">Frontend</div>
        </div>

        {/* Anthropic (Claude) */}
        <div className="text-center">
          <div className={`text-2xl font-bold mb-1 ${getAnthropicColor()}`}>
            {formatAnthropicStatus()}
          </div>
          <div className="text-sm font-medium text-secondary mb-0.5">Anthropic</div>
          <div className="text-xs text-muted">LLM</div>
        </div>
      </div>
    </div>
  );
}
