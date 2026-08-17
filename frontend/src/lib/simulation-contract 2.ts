/**
 * The config contract — the exact object the Python engine consumes.
 *
 * Source of truth is the Python side:
 *   - `intake.FIELDS` -> the 18 FirmSignature fields (FIRM_FIELDS below)
 *   - `optimize.OBJECTIVES` + `parse_guardrails` -> objective weights + guardrail metrics
 *   - `src/models/elasticities.DEFAULT_ELASTICITIES` -> valid elasticity coefficient ids
 *
 * The form (IntakeForm.tsx) builds an IntakeValues, runs it through `buildConfig`, and
 * the result is byte-compatible with what `run_config.build_sim_config` +
 * `build_objective` consume. `validateContract` throws on anything the Python side
 * would reject — so a config written by this module always runs.
 *
 * Pure TS (no Supabase import) so it's unit-testable in isolation.
 */

// ---------------------------------------------------------------------------
// FirmSignature — the 18 intake fields (mirror of intake.py FIELDS)
// ---------------------------------------------------------------------------

export type FirmFieldType = 'float' | 'int' | 'str';

export interface FirmField {
  key: string;
  label: string;
  question: string;
  type: FirmFieldType;
  default: number | string;
  enum?: string[];
  tag: string; // [SURVEY] | [INFERRED] | [ASSUMPTION]
}

export const FIRM_FIELDS: FirmField[] = [
  // --- structural posture ---
  { key: 'pricing_posture', label: 'Pricing', question: 'How do you bill?', type: 'str',
    default: 'hourly', enum: ['hourly', 'partial_afa', 'afa_native'], tag: '[SURVEY]' },
  { key: 'leverage_ratio', label: 'Leverage', question: 'What is your associate-to-partner ratio?',
    type: 'float', default: 3.5, tag: '[SURVEY]' },
  { key: 'origination_concentration', label: 'Origination', question: 'What fraction of origination does your top rainmaker control?',
    type: 'float', default: 0.4, tag: '[INFERRED]' },
  { key: 'practice_mix_transactional', label: 'Practice mix', question: 'What fraction of revenue is transactional?',
    type: 'float', default: 0.35, tag: '[SURVEY]' },
  { key: 'client_concentration', label: 'Client concentration', question: 'What fraction of revenue is your top client?',
    type: 'float', default: 0.3, tag: '[INFERRED]' },
  { key: 'partner_power_mix', label: 'Partner power', question: 'Can one partner block a firm-wide change? (0=no, 1=yes)',
    type: 'float', default: 0.5, tag: '[ASSUMPTION]' },
  // --- Tier 1: work, comp, clients, people ---
  { key: 'tacit_work_share', label: 'Work composition', question: 'What fraction of matters are complex/bet-the-company (vs routine)?',
    type: 'float', default: 0.5, tag: '[INFERRED]' },
  { key: 'comp_model', label: 'Comp model', question: 'Is comp lockstep, modified, or eat_what_you_kill?',
    type: 'str', default: 'modified', enum: ['lockstep', 'modified', 'eat_what_you_kill'], tag: '[INFERRED]' },
  { key: 'client_afa_pressure', label: 'AFA pressure', question: 'Do your clients demand AFA? (0=no pressure, 1=they\'ll leave)',
    type: 'float', default: 0.3, tag: '[SURVEY]' },
  { key: 'partner_retirement_horizon', label: 'Retirement horizon', question: 'Average years until your partners retire?',
    type: 'float', default: 10.0, tag: '[INFERRED]' },
  // --- Tier 2: financials + tech ---
  { key: 'baseline_ppp', label: 'PPP', question: 'Your actual profit per partner ($)?',
    type: 'int', default: 3_000_000, tag: '[SURVEY]' },
  { key: 'baseline_rpl', label: 'RPL', question: 'Your actual revenue per lawyer ($)?',
    type: 'int', default: 1_200_000, tag: '[SURVEY]' },
  { key: 'baseline_realization', label: 'Realization', question: 'Your actual realization rate (%)?',
    type: 'float', default: 85.0, tag: '[SURVEY]' },
  { key: 'baseline_margin', label: 'Margin', question: 'Your actual matter margin (%)?',
    type: 'float', default: 30.0, tag: '[INFERRED]' },
  { key: 'tech_maturity', label: 'Tech maturity', question: 'How mature is your KM/precedent/data infrastructure? (0–1)',
    type: 'float', default: 0.4, tag: '[INFERRED]' },
  // --- culture ---
  { key: 'partner_ai_usage', label: 'Partner AI usage', question: 'What fraction of partners have personally used a legal AI tool?',
    type: 'float', default: 0.69, tag: '[SURVEY]' },
  { key: 'attrition_intensity', label: 'Attrition', question: 'What is your associate attrition rate (as a fraction)?',
    type: 'float', default: 0.19, tag: '[SURVEY]' },
  { key: 'escalation_design', label: 'Escalation design', question: 'Is there a designed escalation path, or whoever-shouts-loudest? (0–1)',
    type: 'float', default: 0.5, tag: '[ASSUMPTION]' },
];

export const FIRM_FIELD_DEFAULTS: Record<string, number | string> =
  Object.fromEntries(FIRM_FIELDS.map((f) => [f.key, f.default]));

export const FIRM_FIELD_KEYS = new Set(FIRM_FIELDS.map((f) => f.key));

// ---------------------------------------------------------------------------
// Objective + guardrails (mirror of optimize.py OBJECTIVES / parse_guardrails)
// ---------------------------------------------------------------------------

/** objective KEY -> metric id (the id used in guardrails and reported metrics) */
export const OBJECTIVES = {
  ppp: 'ppp',
  margin: 'matter_profit_margin',
  rpl: 'rpl',
  realization: 'realization_rate',
  retention: 'associate_attrition',
} as const;

export type ObjectiveKey = keyof typeof OBJECTIVES;
export const OBJECTIVE_KEYS = Object.keys(OBJECTIVES) as ObjectiveKey[];

/** the only metric ids allowed in a guardrail spec */
export const GUARDRAIL_METRICS = new Set<string>(Object.values(OBJECTIVES));

// ---------------------------------------------------------------------------
// Elasticities — the valid coefficient ids (mirror of elasticities.py DEFAULT_ELASTICITIES)
// ---------------------------------------------------------------------------

export interface ElasticityDef {
  id: string;
  name: string;
  base: number;
  low: number;
  high: number;
  /** true when the coefficient has a calibration_question (the 2 exception penalties don't) */
  askable: boolean;
  question?: string;
  lever?: string;
}

export const ELASTICITY_DEFS: ElasticityDef[] = [
  { id: 'margin_ai_afa_gain', name: 'AFA margin conversion', base: 0.15, low: 0.08, high: 0.25, askable: true, lever: 'pricing',
    question: 'On flat-fee matters, when AI cuts the hours, roughly how much of that saving do you keep as margin vs pass to the client?' },
  { id: 'margin_ai_hourly_drag', name: 'Hourly AI drag', base: 0.10, low: 0.05, high: 0.18, askable: true, lever: 'pricing',
    question: 'On hourly matters, when AI does the work faster, do you write down the saved time, or bill it? (more write-down = higher drag)' },
  { id: 'realization_afa_leak', name: 'Hourly-under-AFA-pressure leak', base: 8.0, low: 4.0, high: 12.0, askable: true, lever: 'pricing',
    question: 'When a client pushes for alternative fees and you stay hourly, how much of the bill typically leaks to write-downs?' },
  { id: 'seam_incident_slope', name: 'Seam incident sensitivity', base: 0.7, low: 0.4, high: 0.9, askable: true, lever: 'seams',
    question: 'When you\'ve standardized a workflow before, roughly how much of the rework did it kill? (more = higher slope)' },
  { id: 'margin_redline_penalty', name: 'Redline-rework margin cost', base: 0.02, low: 0.01, high: 0.03, askable: true, lever: 'seams',
    question: 'When a partner substantially rewrites a draft, how much does that cost the matter\'s economics?' },
  { id: 'adoption_comp_gain', name: 'Comp -> adoption lift', base: 0.65, low: 0.35, high: 0.85, askable: true, lever: 'comp',
    question: 'If you tied partner comp to AI use, how much would adoption actually move? (a lot = higher)' },
  { id: 'utilization_ai_cut', name: 'AI utilization compression', base: 3.0, low: 1.5, high: 5.0, askable: true, lever: 'leverage',
    question: 'As AI takes over routine associate work, how much do you expect billable hours per associate to fall?' },
  { id: 'margin_exception_penalty', name: 'Exception margin cost', base: 0.01, low: 0.005, high: 0.02, askable: false },
  { id: 'realization_exception_penalty', name: 'Exception realization cost', base: 0.03, low: 0.015, high: 0.05, askable: false },
  { id: 'attrition_trust_sensitivity', name: 'Trust -> attrition', base: 20.0, low: 10.0, high: 30.0, askable: true,
    question: 'If associates lose faith in how the firm is rolling out AI, how much does that push turnover?' },
];

export const ELASTICITY_IDS = new Set(ELASTICITY_DEFS.map((e) => e.id));

// ---------------------------------------------------------------------------
// Config shape — the exact object the engine consumes
// ---------------------------------------------------------------------------

export interface FirmConfigJson {
  name: string;
  firm_name: string;
  run: {
    sprints: number;
    matters_per_sprint: number;
    seed: number;
    max_cost: number | null;
    model: string;
    legal_tool: string;
  };
  firm: Record<string, string | number>;
  levers: {
    comp_lever_strength: number;
    codify_seams: boolean;
    decision_latency_sprints: number;
  };
  elasticities: Record<string, number>;
  objective: {
    weights: Record<string, number>;
    guardrails: string[];
  };
}

export interface IntakeValues {
  name: string;
  firmName: string;
  firm: Record<string, string | number>;
  levers: {
    compLeverStrength: number;
    codifySeams: boolean;
    decisionLatencySprints: number;
  };
  elasticities: Record<string, number>;
  objective: {
    weights: Record<string, number>;
    guardrails: string[];
  };
  run: {
    sprints: number;
    mattersPerSprint: number;
    seed: number;
    maxCost: number | null;
    model: string;
    legalTool: string;
  };
}

// ---------------------------------------------------------------------------
// Validators — mirror the Python contract's failure modes
// ---------------------------------------------------------------------------

const GUARDRAIL_RE = /^(ppp|matter_profit_margin|rpl|realization_rate|associate_attrition)\s*(<=|>=|<|>)\s*([0-9.]+)$/;

/**
 * Normalize one guardrail spec to "metric<=value" (the engine's canonical form).
 * Throws on an unknown metric, a missing operator, or a non-numeric value —
 * mirroring optimize.parse_guardrails, including `<` -> `<=` and `>` -> `>=`.
 */
export function parseGuardrail(spec: string): string {
  const s = spec.trim();
  const m = GUARDRAIL_RE.exec(s);
  if (!m) {
    if (!/[<=><]/.test(s)) throw new Error(`guardrail "${spec}" needs an operator (<=, >=)`);
    throw new Error(`guardrail "${spec}" must be metric<=value with a known metric`);
  }
  const [, metric, op, val] = m;
  const norm = op === '<' ? '<=' : op === '>' ? '>=' : op;
  return `${metric}${norm}${Number(val)}`;
}

export function parseGuardrails(specs: string[]): string[] {
  return specs.map(parseGuardrail);
}

/** Normalize objective weights to sum 1. Throws on unknown keys or non-positive sum. */
export function normalizeWeights(w: Record<string, number>): Record<string, number> {
  for (const k of Object.keys(w)) {
    if (!(k in OBJECTIVES)) {
      throw new Error(`unknown objective "${k}" (choose from ${OBJECTIVE_KEYS.join(', ')})`);
    }
  }
  const total = Object.values(w).reduce((a, b) => a + b, 0);
  if (total <= 0) throw new Error('objective weights must sum to a positive number');
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(w)) out[k] = v / total;
  return out;
}

/** Throw on any elasticity id the engine doesn't know (mirrors build_elasticities ValueError). */
export function validateElasticities(e: Record<string, number>): void {
  for (const id of Object.keys(e)) {
    if (!ELASTICITY_IDS.has(id)) {
      throw new Error(`unknown elasticity "${id}"; valid: ${[...ELASTICITY_IDS].sort().join(', ')}`);
    }
  }
}

/** Coarse type-check that every firm field is present and of the right type. */
export function validateFirm(firm: Record<string, string | number>): void {
  for (const f of FIRM_FIELDS) {
    const v = firm[f.key];
    if (v === undefined) throw new Error(`missing firm field "${f.key}"`);
    if (f.type === 'str' && typeof v !== 'string') throw new Error(`firm field "${f.key}" must be a string`);
    if (f.type !== 'str' && typeof v !== 'number') throw new Error(`firm field "${f.key}" must be a number`);
    if (f.enum && !f.enum.includes(v as string)) {
      throw new Error(`firm field "${f.key}" must be one of ${f.enum.join(', ')}`);
    }
  }
}

export function validateContract(config: FirmConfigJson): void {
  validateFirm(config.firm);
  normalizeWeights(config.objective.weights); // throws on invalid
  config.objective.guardrails.forEach(parseGuardrail); // throws on invalid
  validateElasticities(config.elasticities); // throws on unknown
}

// ---------------------------------------------------------------------------
// buildConfig — map form input to the exact engine contract object
// ---------------------------------------------------------------------------

export function buildConfig(input: IntakeValues): FirmConfigJson {
  const firm: Record<string, string | number> = { ...FIRM_FIELD_DEFAULTS, ...input.firm };
  const elasticities = { ...input.elasticities };
  const weights = normalizeWeights(input.objective.weights);
  const guardrails = parseGuardrails(input.objective.guardrails);

  const config: FirmConfigJson = {
    name: input.name,
    firm_name: input.firmName,
    run: {
      sprints: input.run.sprints,
      matters_per_sprint: input.run.mattersPerSprint,
      seed: input.run.seed,
      max_cost: input.run.maxCost,
      model: input.run.model,
      legal_tool: input.run.legalTool,
    },
    firm,
    levers: {
      comp_lever_strength: input.levers.compLeverStrength,
      codify_seams: input.levers.codifySeams,
      decision_latency_sprints: input.levers.decisionLatencySprints,
    },
    elasticities,
    objective: { weights, guardrails },
  };

  validateContract(config);
  return config;
}
