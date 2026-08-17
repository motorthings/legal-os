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

      const res = await fetch(`${SIM_API_BASE}/runs`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          config: cfg.config, firm_id: firmId, seeds,
          budget: budget ? Number(budget) : null, provider: 'mock',
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
    <section style={{ border: '1px solid #eee', padding: '1rem', margin: '1.5rem 0' }}>
      <h3>Run the simulation</h3>
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <label>Seeds <input type="number" min={1} max={100} value={seeds} onChange={(e) => setSeeds(e.target.valueAsNumber || 1)} /></label>
        <label>Budget $ <input type="number" placeholder="none" value={budget} onChange={(e) => setBudget(e.target.value)} /></label>
        <button onClick={onRun} disabled={busy || !hasConfig} className="btn-primary border-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">{busy ? 'Launching…' : 'Run baseline'}</button>
      </div>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      {!hasConfig && <p style={{ color: '#888' }}>Save the intake config first to enable runs.</p>}
    </section>
  );
}
