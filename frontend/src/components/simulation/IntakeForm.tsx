'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import {
  FIRM_FIELDS,
  ELASTICITY_DEFS,
  OBJECTIVE_KEYS,
  FIRM_FIELD_DEFAULTS,
  buildConfig,
  type FirmConfigJson,
  type IntakeValues,
} from '@/lib/simulation-contract';

interface Props {
  firmId: string;
  existing?: FirmConfigJson;
}

const DEFAULT_RUN = { sprints: 16, mattersPerSprint: 30, seed: 42, maxCost: 5.0, model: 'deepseek-v4-flash', legalTool: 'mock' };
const ASKABLE = ELASTICITY_DEFS.filter((e) => e.askable);
const DEFAULT_ELASTICITIES = Object.fromEntries(ASKABLE.map((e) => [e.id, e.base]));

function fieldControl(f: (typeof FIRM_FIELDS)[number], value: string | number, onChange: (v: string | number) => void) {
  if (f.enum) {
    return (
      <select value={String(value)} onChange={(e) => onChange(e.target.value)}>
        {f.enum.map((opt) => (
          <option key={opt} value={opt}>{opt.replace(/_/g, ' ')}</option>
        ))}
      </select>
    );
  }
  if (f.type === 'int' || f.type === 'float') {
    return <input type="number" step={f.type === 'int' ? 1 : 'any'} value={Number(value)} onChange={(e) => onChange(e.target.valueAsNumber)} />;
  }
  return <input value={String(value)} onChange={(e) => onChange(e.target.value)} />;
}

export default function IntakeForm({ firmId, existing }: Props) {
  const router = useRouter();
  const [firm, setFirm] = useState<Record<string, string | number>>(
    existing ? { ...FIRM_FIELD_DEFAULTS, ...existing.firm } : { ...FIRM_FIELD_DEFAULTS },
  );
  const [elasticities, setElasticities] = useState<Record<string, number>>({
    ...DEFAULT_ELASTICITIES,
    ...(existing?.elasticities ?? {}),
  });
  const [weights, setWeights] = useState<Record<string, number>>(
    existing?.objective.weights ?? { ppp: 1 },
  );
  const [guardrailsText, setGuardrailsText] = useState(
    (existing?.objective.guardrails ?? []).join(', '),
  );
  const [run, setRun] = useState({ ...DEFAULT_RUN, ...(existing?.run ?? {}) });
  const [name, setName] = useState(existing?.name ?? '');
  const [firmName, setFirmName] = useState(existing?.firm_name ?? '');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const weightTotal = useMemo(() => Object.values(weights).reduce((a, b) => a + b, 0), [weights]);

  function setField(key: string, v: string | number) {
    setFirm((f) => ({ ...f, [key]: v }));
  }

  function setElasticity(id: string, v: number) {
    setElasticities((e) => ({ ...e, [id]: v }));
  }

  function setWeight(key: string, v: number) {
    setWeights((w) => ({ ...w, [key]: v }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);

    const guardrails = guardrailsText
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const intake: IntakeValues = {
      name: name || 'Unnamed firm',
      firmName: firmName || name || 'Unnamed firm',
      firm,
      levers: { compLeverStrength: 0.3, codifySeams: false, decisionLatencySprints: 2 },
      elasticities,
      objective: { weights, guardrails },
      run,
    };

    let config: FirmConfigJson;
    try {
      config = buildConfig(intake); // validates: weights, guardrails, elasticities, firm
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid config');
      setBusy(false);
      return;
    }

    try {
      // versioned upsert: bump the previous active config, then insert the new active one
      const { data: maxRow } = await supabase
        .from('firm_configs')
        .select('version')
        .eq('firm_id', firmId)
        .order('version', { ascending: false })
        .limit(1)
        .maybeSingle();
      const nextVersion = (maxRow?.version ?? 0) + 1;

      await supabase.from('firm_configs').update({ is_active: false }).eq('firm_id', firmId).eq('is_active', true);
      const { error: insErr } = await supabase.from('firm_configs').insert({
        firm_id: firmId, version: nextVersion, config, is_active: true,
      });
      if (insErr) throw insErr;

      await supabase.from('firms').update({ status: 'ready' }).eq('id', firmId);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save config');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ display: 'grid', gap: '1.5rem', maxWidth: 640 }}>
      <section>
        <h3>Identity</h3>
        <label>Run label
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. mid-market demo" />
        </label>
        <label>Firm name
          <input value={firmName} onChange={(e) => setFirmName(e.target.value)} placeholder="e.g. Aldrich & Vale LLP" />
        </label>
      </section>

      {(() => {
        const SECTIONS: Array<[number, string]> = [
          [0, 'Structural posture'],
          [6, 'Work, comp, clients, people'],
          [10, 'Financials & tech'],
          [15, 'Culture'],
        ];
        return FIRM_FIELDS.map((f, i) => (
          <div key={f.key}>
          {SECTIONS.find(([start]) => start === i) && <h3>{SECTIONS.find(([start]) => start === i)![1]}</h3>}
          <label>
            <strong>{f.label}</strong> <span style={{ color: '#999' }}>{f.tag}</span>
            <div style={{ color: '#666', fontSize: '0.85rem' }}>{f.question}</div>
            {fieldControl(f, firm[f.key], (v) => setField(f.key, v))}
          </label>
          </div>
        ));
      })()}

      <section>
        <h3>Priorities</h3>
        <div style={{ display: 'grid', gap: '0.4rem' }}>
          {OBJECTIVE_KEYS.map((k) => (
            <label key={k}>
              {k}
              <input
                type="number" step="0.1" min="0"
                value={weights[k] ?? 0}
                onChange={(e) => setWeight(k, e.target.valueAsNumber || 0)}
              />
            </label>
          ))}
          <p>Sum: {weightTotal.toFixed(2)} (normalized to 1 on save)</p>
        </div>
        <label>
          Guardrails (comma-separated, e.g. <code>associate_attrition&lt;=25, realization_rate&gt;=70</code>)
          <input value={guardrailsText} onChange={(e) => setGuardrailsText(e.target.value)} />
        </label>
      </section>

      <section>
        <h3>Calibration — how strongly the levers work at your firm</h3>
        {ASKABLE.map((e) => (
          <label key={e.id}>
            <strong>{e.name}</strong> <span style={{ color: '#999' }}>[{e.low}–{e.high}]</span>
            <div style={{ color: '#666', fontSize: '0.85rem' }}>{e.question}</div>
            <input
              type="range" min={e.low} max={e.high} step="any"
              value={elasticities[e.id]}
              onChange={(ev) => setElasticity(e.id, Number(ev.target.value))}
            />
            <span>{elasticities[e.id]}</span>
          </label>
        ))}
      </section>

      <section>
        <h3>Run scale</h3>
        <label>Sprints <input type="number" value={run.sprints} onChange={(e) => setRun({ ...run, sprints: e.target.valueAsNumber })} /></label>
        <label>Model
          <select value={run.model} onChange={(e) => setRun({ ...run, model: e.target.value })}>
            <option value="deepseek-v4-flash">deepseek-v4-flash (iteration)</option>
            <option value="deepseek-v4-pro">deepseek-v4-pro (client pass)</option>
          </select>
        </label>
        <label>Legal tool
          <select value={run.legalTool} onChange={(e) => setRun({ ...run, legalTool: e.target.value })}>
            {['mock', 'descrybe', 'harvey', 'cocounsel', 'westlaw_ai', 'lexis_ai'].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </label>
      </section>

      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      <button type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save config'}</button>
    </form>
  );
}
