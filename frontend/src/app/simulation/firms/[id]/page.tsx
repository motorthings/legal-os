'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { supabase } from '@/lib/supabase';
import type { FirmConfigJson } from '@/lib/simulation-contract';
import IntakeForm from '@/components/simulation/IntakeForm';
import { RunSection } from '@/components/simulation/RunSection';
import RunHistory from '@/components/simulation/RunHistory';

export default function FirmPage() {
  const params = useParams<{ id: string }>();
  const firmId = params.id;
  const [firmName, setFirmName] = useState('Loading…');
  const [config, setConfig] = useState<FirmConfigJson | undefined>(undefined);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    const { data: firm } = await supabase.from('firms').select('name, status').eq('id', firmId).maybeSingle();
    if (firm) setFirmName(firm.name);
    const { data: cfg } = await supabase
      .from('firm_configs')
      .select('config')
      .eq('firm_id', firmId)
      .eq('is_active', true)
      .maybeSingle();
    setConfig((cfg as { config?: FirmConfigJson } | null)?.config);
    setLoaded(true);
  }, [firmId]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main style={{ maxWidth: 960, margin: '0 auto', padding: '2rem 1rem' }}>
      <Link href="/simulation" style={{ color: '#888', textDecoration: 'none' }}>← All firms</Link>
      <h1>{firmName}</h1>
      {!loaded ? <p>Loading…</p> : (
        <>
          <h2 className="text-xl font-bold text-[var(--text)] tracking-tight mb-4">Intake</h2>
          <IntakeForm firmId={firmId} existing={config} />
          <RunSection firmId={firmId} hasConfig={!!config} />
          <details className="card p-4 mb-4">
            <summary className="cursor-pointer select-none font-semibold text-[var(--text)]">Runs</summary>
            <div className="mt-3">
              <RunHistory firmId={firmId} />
            </div>
          </details>
        </>
      )}
    </main>
  );
}
