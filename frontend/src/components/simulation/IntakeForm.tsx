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
const GUARDRAIL_METRICS = [
  { key: 'ppp', label: 'Profit per partner' },
  { key: 'matter_profit_margin', label: 'Matter margin' },
  { key: 'rpl', label: 'Revenue per lawyer' },
  { key: 'realization_rate', label: 'Realization' },
  { key: 'associate_attrition', label: 'Associate attrition' },
];
const ASKABLE = ELASTICITY_DEFS.filter((e) => e.askable);
const DEFAULT_ELASTICITIES = Object.fromEntries(ASKABLE.map((e) => [e.id, e.base]));

const OBJECTIVE_LABELS: Record<string, string> = {
  ppp: 'Profit per partner',
  margin: 'Matter margin',
  rpl: 'Revenue per lawyer',
  realization: 'Realization',
  retention: 'Retention',
};

const TAG_COLOR: Record<string, string> = {
  '[SURVEY]': 'var(--secondary)',
  '[INFERRED]': 'var(--metric)',
  '[ASSUMPTION]': 'var(--amber)',
};

const FIRM_SECTIONS: { title: string; fields: (typeof FIRM_FIELDS)[number][] }[] = [
  { title: 'Structural posture', fields: FIRM_FIELDS.slice(0, 6) },
  { title: 'Work, comp & clients', fields: FIRM_FIELDS.slice(6, 10) },
  { title: 'Financials & tech', fields: FIRM_FIELDS.slice(10, 15) },
  { title: 'Culture', fields: FIRM_FIELDS.slice(15, 18) },
];

const INPUT_CLS = 'px-2.5 py-1.5 text-[13px] rounded-md';

function fieldControl(f: (typeof FIRM_FIELDS)[number], value: string | number, onChange: (v: string | number) => void) {
  if (f.enum) {
    return (
      <select className={INPUT_CLS} value={String(value)} onChange={(e) => onChange(e.target.value)}>
        {f.enum.map((opt) => (
          <option key={opt} value={opt}>{opt.replace(/_/g, ' ')}</option>
        ))}
      </select>
    );
  }
  if (f.type === 'int' || f.type === 'float') {
    return <input className={INPUT_CLS} type="number" step={f.type === 'int' ? 1 : 'any'} value={Number(value)} onChange={(e) => onChange(e.target.valueAsNumber)} />;
  }
  return <input className={INPUT_CLS} value={String(value)} onChange={(e) => onChange(e.target.value)} />;
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
  const [weights, setWeights] = useState<Record<string, number>>(() => {
    const base: Record<string, number> = { ppp: 1, margin: 0, rpl: 0, realization: 0, retention: 0 };
    return existing?.objective.weights ? { ...base, ...existing.objective.weights } : base;
  });
  const [guardrails, setGuardrails] = useState<Record<string, { min: string; max: string }>>(() => {
    const init: Record<string, { min: string; max: string }> = {};
    for (const m of GUARDRAIL_METRICS) init[m.key] = { min: '', max: '' };
    for (const spec of existing?.objective.guardrails ?? []) {
      const match = spec.match(/^(\w+)(<=|>=)(.+)$/);
      if (match) {
        const [, key, op, val] = match;
        if (op === '>=') init[key].min = val;
        else init[key].max = val;
      }
    }
    return init;
  });
  const [run, setRun] = useState({ ...DEFAULT_RUN, ...(existing?.run ?? {}) });
  const [name, setName] = useState(existing?.name ?? '');
  const [firmName, setFirmName] = useState(existing?.firm_name ?? '');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const weightPct = useMemo(
    () => Math.round(OBJECTIVE_KEYS.reduce((s, k) => s + (weights[k] ?? 0), 0) * 100),
    [weights],
  );

  function setField(key: string, v: string | number) {
    setFirm((f) => ({ ...f, [key]: v }));
  }

  function setElasticity(id: string, v: number) {
    setElasticities((e) => ({ ...e, [id]: v }));
  }

  // Move one priority slider while keeping the total pinned to 1: the delta is
  // absorbed (proportionally) by the other sliders, then renormalized.
  function setWeight(key: string, raw: number) {
    const target = Math.max(0, Math.min(1, raw));
    setWeights((prev) => {
      const current = prev[key] ?? 0;
      const diff = target - current;
      if (diff === 0) return prev;
      const others = OBJECTIVE_KEYS.filter((k) => k !== key);
      const othersTotal = others.reduce((s, k) => s + (prev[k] ?? 0), 0);
      const next: Record<string, number> = { ...prev, [key]: target };
      if (othersTotal > 1e-9) {
        for (const k of others) {
          next[k] = Math.max(0, (prev[k] ?? 0) - diff * ((prev[k] ?? 0) / othersTotal));
        }
      } else {
        const share = Math.max(0, -diff) / others.length;
        for (const k of others) next[k] = share;
      }
      const total = OBJECTIVE_KEYS.reduce((s, k) => s + next[k], 0);
      if (total > 0) for (const k of OBJECTIVE_KEYS) next[k] = next[k] / total;
      return next;
    });
  }

  function setGuardrail(key: string, field: 'min' | 'max', value: string) {
    setGuardrails((g) => ({ ...g, [key]: { ...g[key], [field]: value } }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);

    const guardrailSpecs = GUARDRAIL_METRICS.flatMap((m) => {
      const { min, max } = guardrails[m.key];
      const specs: string[] = [];
      if (min !== '') specs.push(`${m.key}>=${min}`);
      if (max !== '') specs.push(`${m.key}<=${max}`);
      return specs;
    });

    const intake: IntakeValues = {
      name: name || 'Unnamed firm',
      firmName: firmName || name || 'Unnamed firm',
      firm,
      levers: { compLeverStrength: 0.3, codifySeams: false, decisionLatencySprints: 2 },
      elasticities,
      objective: { weights, guardrails: guardrailSpecs },
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
    <form onSubmit={onSubmit} className="flex flex-col gap-4 max-w-4xl">
      {/* Identity */}
      <section className="card p-5">
        <h3 className="font-mono text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">Identity</h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-[13px] font-semibold text-[var(--text)]">Run label</span>
            <input className={INPUT_CLS} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. mid-market demo" />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[13px] font-semibold text-[var(--text)]">Firm name</span>
            <input className={INPUT_CLS} value={firmName} onChange={(e) => setFirmName(e.target.value)} placeholder="e.g. Aldrich & Vale LLP" />
          </label>
        </div>
      </section>

      {/* Firm signature */}
      {FIRM_SECTIONS.map((sec) => (
        <section key={sec.title} className="card p-5">
          <h3 className="font-mono text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">{sec.title}</h3>
          <div className="grid gap-x-5 gap-y-3.5 sm:grid-cols-2 lg:grid-cols-3">
            {sec.fields.map((f) => (
              <label key={f.key} className="flex flex-col gap-1 min-w-0">
                <span className="flex items-baseline gap-2">
                  <span className="text-[13px] font-semibold text-[var(--text)]">{f.label}</span>
                  <span className="font-mono text-[9px] tracking-wide" style={{ color: TAG_COLOR[f.tag] }}>{f.tag}</span>
                </span>
                <span className="text-[11px] text-[var(--text-muted)] leading-snug">{f.question}</span>
                {fieldControl(f, firm[f.key], (v) => setField(f.key, v))}
              </label>
            ))}
          </div>
        </section>
      ))}

      {/* Priorities */}
      <section className="card p-5">
        <h3 className="font-mono text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-1">Priorities</h3>
        <p className="text-[12px] text-[var(--text-muted)] mb-3">Weight the objectives that matter most — the total always stays at 100%.</p>
        <div className="flex flex-col gap-2.5">
          {OBJECTIVE_KEYS.map((k) => (
            <div key={k} className="flex items-center gap-3">
              <span className="w-36 shrink-0 text-[13px] text-[var(--text-dim)]">{OBJECTIVE_LABELS[k] ?? k}</span>
              <input
                type="range" min={0} max={1} step={0.01} className="flex-1"
                value={weights[k] ?? 0}
                onChange={(e) => setWeight(k, Number(e.target.value))}
              />
              <span className="w-11 shrink-0 text-right font-mono text-[12px] text-[var(--text)]">
                {Math.round((weights[k] ?? 0) * 100)}%
              </span>
            </div>
          ))}
        </div>
        <div className="mt-3 text-right font-mono text-[11px] text-[var(--text-muted)]">Total: {weightPct}%</div>
      </section>

      {/* Guardrails */}
      <section className="card p-5">
        <h3 className="font-mono text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-1">Guardrails</h3>
        <p className="text-[12px] text-[var(--text-muted)] mb-3">Constraints the recommendation must satisfy (leave blank for none).</p>
        <div className="grid gap-x-8 gap-y-2.5 sm:grid-cols-2">
          {GUARDRAIL_METRICS.map((m) => (
            <div key={m.key} className="flex items-center gap-2">
              <span className="flex-1 text-[13px] text-[var(--text-dim)]">{m.label}</span>
              <span className="text-[var(--text-muted)]">≥</span>
              <input type="number" placeholder="min" className="w-20 px-2 py-1 text-[13px] rounded-md" value={guardrails[m.key].min} onChange={(e) => setGuardrail(m.key, 'min', e.target.value)} />
              <span className="text-[var(--text-muted)]">≤</span>
              <input type="number" placeholder="max" className="w-20 px-2 py-1 text-[13px] rounded-md" value={guardrails[m.key].max} onChange={(e) => setGuardrail(m.key, 'max', e.target.value)} />
            </div>
          ))}
        </div>
      </section>

      {/* Calibration */}
      <section className="card p-5">
        <h3 className="font-mono text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-1">Calibration</h3>
        <p className="text-[12px] text-[var(--text-muted)] mb-3">How strongly the levers work at your firm.</p>
        <div className="flex flex-col gap-3">
          {ASKABLE.map((e) => (
            <label key={e.id} className="flex flex-col gap-1">
              <div className="flex items-baseline gap-2">
                <span className="text-[13px] font-semibold text-[var(--text)]">{e.name}</span>
                <span className="font-mono text-[10px] text-[var(--text-muted)]">[{e.low}–{e.high}]</span>
              </div>
              <span className="text-[11px] text-[var(--text-muted)] leading-snug">{e.question}</span>
              <div className="flex items-center gap-3">
                <input
                  type="range" min={e.low} max={e.high} step="any" className="flex-1"
                  value={elasticities[e.id]}
                  onChange={(ev) => setElasticity(e.id, Number(ev.target.value))}
                />
                <span className="w-14 text-right font-mono text-[12px] text-[var(--text)]">{elasticities[e.id]}</span>
              </div>
            </label>
          ))}
        </div>
      </section>

      {/* Run scale */}
      <section className="card p-5">
        <h3 className="font-mono text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">Run scale</h3>
        <div className="grid gap-4 sm:grid-cols-3">
          <label className="flex flex-col gap-1">
            <span className="text-[13px] font-semibold text-[var(--text)]">Sprints</span>
            <input className={INPUT_CLS} type="number" value={run.sprints} onChange={(e) => setRun({ ...run, sprints: e.target.valueAsNumber })} />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[13px] font-semibold text-[var(--text)]">Model</span>
            <select className={INPUT_CLS} value={run.model} onChange={(e) => setRun({ ...run, model: e.target.value })}>
              <option value="deepseek-v4-flash">deepseek-v4-flash (iteration)</option>
              <option value="deepseek-v4-pro">deepseek-v4-pro (client pass)</option>
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[13px] font-semibold text-[var(--text)]">Legal tool</span>
            <select className={INPUT_CLS} value={run.legalTool} onChange={(e) => setRun({ ...run, legalTool: e.target.value })}>
              {['mock', 'descrybe', 'harvey', 'cocounsel', 'westlaw_ai', 'lexis_ai'].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {error && <p className="text-sm text-[var(--rose)]">{error}</p>}
      <button type="submit" disabled={busy} className="btn-primary border-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed self-start">
        {busy ? 'Saving…' : 'Save config'}
      </button>
    </form>
  );
}
