'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { SIM_API_BASE } from '@/lib/simulation-api';

export function RunSection({ firmId, hasConfig }: { firmId: string; hasConfig: boolean }) {
  const router = useRouter();
  const [seeds, setSeeds] = useState(20);
  const [budget, setBudget] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onRun() {
    setError(null);
    setBusy(true);
    try {
      const { data: cfg } = await supabase
        .from('firm_configs')
        .select('config')
        .eq('firm_id', firmId)
        .eq('is_active', true)
        .maybeSingle();
      if (!cfg) throw new Error('no active config — fill the intake form first');

      const model = cfg.config?.run?.model ?? 'mock';
      const provider = model === 'mock' ? 'mock' : 'deepseek';

      const res = await fetch(`${SIM_API_BASE}/runs`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          config: cfg.config, firm_id: firmId, seeds,
          budget: budget ? Number(budget) : null, provider,
        }),
      });
      if (!res.ok) throw new Error(`run launch failed: ${res.status}`);
      const { run_id } = await res.json();
      router.push(`/simulation/firms/${firmId}/runs/${run_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'launch failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card p-4 mb-4">
      <h3 className="text-[15px] font-bold text-[var(--text)] tracking-tight mb-3">Run the simulation</h3>
      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-1.5">
          <span className="text-[13px] font-semibold text-[var(--text)]">Seeds</span>
          <input type="number" min={1} max={100} className="w-20 px-2 py-1 text-[13px] rounded-md" value={seeds} onChange={(e) => setSeeds(e.target.valueAsNumber || 1)} />
        </label>
        <label className="flex items-center gap-1.5">
          <span className="text-[13px] font-semibold text-[var(--text)] whitespace-nowrap">Budget $</span>
          <input type="number" placeholder="none" className="w-20 px-2 py-1 text-[13px] rounded-md" value={budget} onChange={(e) => setBudget(e.target.value)} />
        </label>
        <button onClick={onRun} disabled={busy || !hasConfig} className="btn-primary border-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">{busy ? 'Launching…' : 'Run baseline'}</button>
      </div>
      {error && <p className="text-sm text-[var(--rose)] mt-2">{error}</p>}
      {!hasConfig && <p className="text-[12px] text-[var(--text-muted)] mt-2">Save the intake config first to enable runs.</p>}
    </section>
  );
}
