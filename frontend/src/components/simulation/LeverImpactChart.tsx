'use client';

import { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid,
} from 'recharts';

// Each change's effect on profit per partner, measured on its own against standing still.
// Rendered as a horizontal bar (green = helps, red = costs) so a partner sees at a glance
// which levers carry the plan and which only matter once the others are in.

const LEVER_NAME: Record<string, string> = {
  pricing: 'Flat-fee pricing',
  seams: 'Codified hand-offs',
  comp: 'AI-adoption pay',
  latency: 'Faster action',
  leverage: 'Flatter pyramid',
};

const fmtM = (v: number) => `$${(v / 1_000_000).toFixed(2)}M`;

export default function LeverImpactChart({
  effects,
}: {
  effects: Record<string, { delta_ppp?: number }> | undefined;
}) {
  const data = useMemo(() => {
    if (!effects) return null;
    return Object.entries(effects)
      .filter(([, fx]) => typeof fx.delta_ppp === 'number')
      .map(([key, fx]) => ({ name: LEVER_NAME[key] ?? key, value: fx.delta_ppp! }))
      .sort((a, b) => b.value - a.value);
  }, [effects]);

  if (!data || data.length === 0) return null;

  return (
    <div className="border border-[var(--border)] rounded-lg p-3">
      <div className="text-[12px] text-[var(--text-dim)] mb-1">
        Each change, on its own — effect on profit per partner
      </div>
      <ResponsiveContainer width="100%" height={data.length * 44}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 0, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => fmtM(v)}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={130}
            tick={{ fontSize: 11, fill: 'var(--text)' }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            formatter={(value) => [fmtM(value as number), 'Profit per partner']}
            labelFormatter={() => ''}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={22}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.value >= 0 ? '#10b981' : '#ef4444'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
