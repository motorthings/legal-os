'use client';

import { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { SIM_API_BASE } from '@/lib/simulation-api';

const METRICS: { key: string; label: string; color: string }[] = [
  { key: 'ppp', label: 'Profit per partner', color: '#2dd4bf' },
  { key: 'matter_profit_margin', label: 'Matter margin', color: '#a78bfa' },
  { key: 'realization_rate', label: 'Realization', color: '#f37021' },
  { key: 'associate_attrition', label: 'Attrition', color: '#f59e0b' },
  { key: 'rpl', label: 'Revenue per lawyer', color: '#34d399' },
];

export default function MetricsCharts({ runId }: { runId: string }) {
  const [data, setData] = useState<Record<string, number[]> | null>(null);

  useEffect(() => {
    fetch(`${SIM_API_BASE}/runs/${runId}/metrics`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => setData(null));
  }, [runId]);

  if (!data) return null;
  const sprints = Math.max(0, ...Object.values(data).map((a) => a.length));
  if (sprints === 0) return null;

  const rows = Array.from({ length: sprints }, (_, i) => {
    const row: Record<string, number> = { sprint: i + 1 };
    for (const m of METRICS) {
      const arr = data[m.key];
      if (arr && arr[i] !== undefined) row[m.key] = arr[i];
    }
    return row;
  });

  return (
    <div className="mt-6">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
        Metric trajectories
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {METRICS.filter((m) => data[m.key]).map((m) => (
          <div key={m.key} className="border border-[var(--border)] rounded-lg p-3">
            <div className="text-[12px] text-[var(--text-dim)] mb-1">{m.label}</div>
            <ResponsiveContainer width="100%" height={150}>
              <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="sprint" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickLine={false} axisLine={false} width={48} />
                <Tooltip />
                <Line type="monotone" dataKey={m.key} stroke={m.color} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>
    </div>
  );
}
