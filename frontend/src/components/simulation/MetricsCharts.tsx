'use client';

import { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine, Legend,
} from 'recharts';
import { SIM_API_BASE } from '@/lib/simulation-api';

// The one money chart: profit per partner, quarter by quarter. When the payload carries
// the Monte-Carlo trajectories, draw baseline (teal) vs recommended (green) as two curves
// on the same axes; otherwise fall back to the single-scenario baseline plus a flat
// "Recommended" reference line.

export default function MetricsCharts({
  runId,
  baseline,
  recommended,
  reference,
}: {
  runId: string;
  baseline?: number[] | null;
  recommended?: number[] | null;
  reference?: { value: number; label: string };
}) {
  const [fetched, setFetched] = useState<number[] | null>(null);

  useEffect(() => {
    if (baseline && baseline.length > 0) return; // payload trajectory wins over /metrics
    fetch(`${SIM_API_BASE}/runs/${runId}/metrics`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setFetched(d?.ppp ?? null))
      .catch(() => setFetched(null));
  }, [runId, baseline]);

  const ppp = baseline && baseline.length > 0 ? baseline : fetched;
  if (!ppp || ppp.length === 0) return null;

  const hasRecommendedLine = !!(recommended && recommended.length > 0);
  const n = Math.max(ppp.length, recommended?.length ?? 0);
  const rows = Array.from({ length: n }, (_, i) => ({
    sprint: i + 1,
    baseline: ppp[i] ?? null,
    recommended: hasRecommendedLine ? recommended![i] ?? null : null,
  }));

  return (
    <div className="border border-[var(--border)] rounded-lg p-3 my-4">
      <div className="text-[12px] text-[var(--text-dim)] mb-1">
        Profit per partner, quarter by quarter
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="sprint" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickLine={false} axisLine={false} />
          <YAxis
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false}
            axisLine={false}
            width={52}
            tickFormatter={(v: number) => `$${(v / 1_000_000).toFixed(1)}M`}
          />
          <Tooltip
            formatter={(value, name) => [`$${(Number(value) / 1_000_000).toFixed(2)}M`, name]}
            labelFormatter={(l) => `Quarter ${l}`}
          />
          {!hasRecommendedLine && reference && (
            <ReferenceLine
              y={reference.value}
              stroke="#10b981"
              strokeDasharray="4 4"
              strokeWidth={2}
              ifOverflow="extendDomain"
              label={{ value: reference.label, position: 'insideTopRight', fill: '#10b981', fontSize: 11 }}
            />
          )}
          <Line type="monotone" dataKey="baseline" stroke="#2dd4bf" strokeWidth={2} dot={false} name="Baseline" />
          {hasRecommendedLine && (
            <Line type="monotone" dataKey="recommended" stroke="#10b981" strokeWidth={2.5} dot={false} name="Recommended" />
          )}
          <Legend iconType="line" wrapperStyle={{ fontSize: 11, color: 'var(--text-muted)' }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
