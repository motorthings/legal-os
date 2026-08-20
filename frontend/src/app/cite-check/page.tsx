'use client';

import { useEffect, useRef, useState } from 'react';
import { useAuth } from '@/lib/auth';
import {
  FileCheck2, Play, Loader2, Download, AlertTriangle, ShieldCheck, ShieldAlert, HelpCircle,
  CheckCircle2, XCircle, Quote, Scale,
} from 'lucide-react';

interface CiteCheckReport {
  provider?: string;
  tools?: string[];
  total_references: number;
  resolved: number;
  unresolved: number;
  good_law: number;
  caution: number;
  bad_law: number;
  unknown: number;
  quotes_checked: number;
  quotes_verified: number;
  quotes_failed: number;
  quotes_unverifiable?: number;
  references: {
    citation?: string;
    case_title: string;
    case_id?: string;
    status: 'good' | 'caution' | 'bad' | 'unknown';
    treatment_category?: string;
    resolution_confidence?: string;
  }[];
  quotes?: QuoteResult[];
  fixes?: {
    misquotes?: { quote: string; case?: string; citation?: string; correct_passage?: string; error?: string; corpus_verdict?: string; corpus_note?: string; correct_case?: { title?: string; citation?: string } }[];
    caution?: { case?: string; citation?: string; treatment_category?: string; negative_citing?: { title?: string; case_id?: string; treatment?: { category?: string } }[]; error?: string }[];
    unknown?: { case?: string; citation?: string; confirmed?: boolean; summary?: string; error?: string }[];
  };
}

interface QuoteResult {
  text: string;
  attributed_to?: string | null;
  citation?: string;
  verified?: boolean | null;
  category?: 'verified' | 'misquote' | 'unverifiable';
  reason?: string;
}

function statusStyle(status: string) {
  switch (status) {
    case 'good': return { bg: 'rgba(34,197,94,0.12)', text: '#22c55e', border: 'rgba(34,197,94,0.25)', label: 'Good Law', icon: ShieldCheck };
    case 'bad': return { bg: 'rgba(239,68,68,0.12)', text: '#ef4444', border: 'rgba(239,68,68,0.25)', label: 'Bad Law', icon: ShieldAlert };
    case 'caution': return { bg: 'rgba(245,158,11,0.12)', text: '#f59e0b', border: 'rgba(245,158,11,0.25)', label: 'Caution', icon: AlertTriangle };
    default: return { bg: 'rgba(100,116,139,0.12)', text: '#94a3b8', border: 'rgba(100,116,139,0.25)', label: 'Unknown', icon: HelpCircle };
  }
}

export default function CiteCheckPage() {
  const { session } = useAuth();
  const [text, setText] = useState('');
  const [name, setName] = useState('');
  const [running, setRunning] = useState(false);
  const [runningMode, setRunningMode] = useState<'normal' | 'deep' | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [report, setReport] = useState<CiteCheckReport | null>(null);
  const [brief, setBrief] = useState<{ name: string; content: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  const handleRun = async (deep: boolean) => {
    if (!text.trim() || running) return;
    setRunning(true);
    setRunningMode(deep ? 'deep' : 'normal');
    setLogs([]);
    setReport(null);
    setBrief(null);
    setError(null);

    const API_URL =
      process.env.NEXT_PUBLIC_LEGAL_OS_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8080';
    const token = session?.access_token;

    try {
      const res = await fetch(`${API_URL}/api/legal-research/cite-check`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text, name: name || undefined, deep }),
      });

      if (!res.ok || !res.body) {
        const errText = await res.text();
        throw new Error(`Cite check failed (${res.status}): ${errText}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx: number;
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const raw = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          for (const line of raw.split('\n')) {
            if (!line.startsWith('data: ')) continue;
            let payload: any;
            try { payload = JSON.parse(line.slice(6)); } catch { continue; }
            if (payload.type === 'log') setLogs((p) => [...p, payload.message]);
            else if (payload.type === 'error') setError(payload.message);
            else if (payload.type === 'report') setReport(payload.report);
            else if (payload.type === 'brief') setBrief({ name: payload.name, content: payload.content });
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Cite check failed');
    } finally {
      setRunning(false);
      setRunningMode(null);
    }
  };

  const handleDownload = () => {
    if (!brief) return;
    const blob = new Blob([brief.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = brief.name;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] mt-3 mb-2">Cite Check</h1>
        <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
          Validate a brief against the Descrybe Legal Engine — citations confirmed, quotes verified
          word-for-word, good-law status flagged. Watch it work live.
        </p>
      </header>

      {/* Input */}
      <div className="card p-6 mb-6">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={running}
          placeholder="Brief name (optional) — e.g. JAMS Demand"
          className="w-full rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50 mb-3"
          style={{ background: 'var(--surface2)' }}
        />
        <textarea
          rows={10}
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={running}
          placeholder="Paste the brief or filing text here — citations and quoted passages will be extracted and validated…"
          className="w-full rounded-lg border border-[var(--border)] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/50 font-mono resize-y disabled:opacity-50"
          style={{ background: 'var(--surface2)' }}
        />
        <div className="mt-3 flex flex-col items-end gap-2 sm:flex-row sm:items-center sm:justify-end">
          <p className="text-xs text-[var(--text-muted)] mr-auto max-w-md">
            Detailed run also pulls correct passages for misquotes and drills caution/unknown cites — slower.
          </p>
          <button
            onClick={() => handleRun(false)}
            disabled={running || !text.trim()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium border border-[var(--border)] text-[var(--text)] hover:bg-[var(--surface2)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {running && runningMode === 'normal' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {running && runningMode === 'normal' ? 'Running…' : 'Run Cite Check'}
          </button>
          <button
            onClick={() => handleRun(true)}
            disabled={running || !text.trim()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white bg-[var(--primary)] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {running && runningMode === 'deep' ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
            {running && runningMode === 'deep' ? 'Running deep pass…' : 'Run Detailed Pass'}
          </button>
        </div>
      </div>

      {/* Live log */}
      {(running || logs.length > 0) && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <FileCheck2 className="w-4 h-4 text-[var(--text-muted)]" />
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Descrybe activity log
            </span>
          </div>
          <div
            ref={logRef}
            className="rounded-lg p-4 font-mono text-xs leading-relaxed max-h-72 overflow-y-auto"
            style={{ background: '#0d1117', color: '#c9d1d9', border: '1px solid #30363d' }}
          >
            {logs.map((l, i) => (
              <div key={i} className={l.startsWith('  ') ? 'pl-4 text-[#8b949e]' : 'text-[#c9d1d9]'}>
                <span className="text-[#58a6ff]">$</span> {l}
              </div>
            ))}
            {running && (
              <div className="text-[#58a6ff]">
                <span className="animate-pulse">▊</span> working…
              </div>
            )}
          </div>
        </div>
      )}

      {error && (
        <div className="card p-6 border-l-4 border-l-[var(--rose)] mb-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-[var(--rose)] flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-[var(--rose)] mb-1">Cite check failed</h3>
              <p className="text-sm text-[var(--text-dim)] break-words">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Report */}
      {report && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Scale className="w-4 h-4 text-[var(--text-muted)]" />
            <h2 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Findings — {report.provider ?? 'Descrybe Legal Engine'}
            </h2>
            {report.tools && report.tools.length > 0 && (
              <span className="text-[10px] text-[var(--text-muted)] font-mono">
                via {report.tools.join(', ')}
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            {[
              { label: 'References', value: report.total_references, color: 'var(--text)' },
              { label: 'Good law', value: report.good_law, color: '#22c55e' },
              { label: 'Caution', value: report.caution, color: '#f59e0b' },
              { label: 'Bad law', value: report.bad_law, color: '#ef4444' },
              { label: 'Quotes verified', value: report.quotes_verified, color: '#22c55e' },
              { label: 'Misquotes', value: report.quotes_failed, color: '#ef4444' },
              { label: 'Non-case quotes', value: report.quotes_unverifiable ?? 0, color: '#94a3b8' },
            ].map((s) => (
              <div key={s.label} className="card p-4">
                <div className="text-2xl font-bold font-mono" style={{ color: s.color }}>{s.value}</div>
                <div className="text-xs text-[var(--text-muted)] mt-1">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="space-y-2">
            {report.references.map((r, i) => {
              const s = statusStyle(r.status);
              const Icon = s.icon;
              return (
                <div key={i} className="card p-4 flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--text)] leading-snug">{r.case_title}</p>
                    <p className="text-xs font-mono text-[var(--text-muted)] mt-0.5 truncate">{r.citation}</p>
                  </div>
                  <span
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium font-mono flex-shrink-0"
                    style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {s.label}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Quotes — misquotes and exceptions surfaced for action */}
          {report.quotes && report.quotes.length > 0 && (() => {
            const misquotes = report.quotes.filter((q) => q.category === 'misquote');
            const unverifiable = report.quotes.filter((q) => q.category === 'unverifiable');
            const fixByQuote = new Map((report.fixes?.misquotes ?? []).map((f) => [f.quote, f]));
            return (
              <div className="mt-6 space-y-4">
                {misquotes.length > 0 && (
                  <div>
                    <h3 className="font-mono text-xs font-semibold uppercase tracking-wider text-[#ef4444] mb-2">
                      Misquotes — {misquotes.length} (case resolved, text not found)
                    </h3>
                    <div className="space-y-2">
                      {misquotes.map((q, i) => {
                        const fix = fixByQuote.get(q.text);
                        return (
                          <div key={i} className="card p-4 border-l-4" style={{ borderLeftColor: '#ef4444' }}>
                            <p className="text-sm text-[var(--text)] leading-snug">“{q.text}”</p>
                            <p className="text-xs font-mono text-[var(--text-muted)] mt-1">
                              → {q.attributed_to ?? 'case'}{q.citation ? ` · ${q.citation}` : ''}
                            </p>
                            {fix?.correct_passage && (
                              <p className="text-xs text-[#22c55e] mt-2 leading-relaxed">
                                <span className="font-semibold">Opinion says:</span> “{fix.correct_passage}”
                              </p>
                            )}
                            {fix?.corpus_verdict && (
                              <p
                                className="text-xs mt-2 leading-relaxed"
                                style={{ color: fix.corpus_verdict === 'found_in_cited_case' ? '#22c55e' : fix.corpus_verdict === 'found_nowhere' ? '#ef4444' : '#f59e0b' }}
                              >
                                <span className="font-semibold font-mono">{fix.corpus_verdict}:</span> {fix.corpus_note}
                              </p>
                            )}
                            {!fix && (
                              <p className="text-xs text-[var(--text-muted)] mt-2">Run a Detailed Pass to pull the correct language and search the corpus.</p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
                {unverifiable.length > 0 && (
                  <details className="card p-4">
                    <summary className="cursor-pointer text-sm font-medium text-[var(--text-dim)]">
                      Non-case quotes — {unverifiable.length} · no action needed (filing prose, JAMS rules, party terms — not case quotations)
                    </summary>
                    <div className="mt-3 space-y-2">
                      {unverifiable.map((q, i) => (
                        <div key={i} className="text-xs">
                          <p className="text-[var(--text)]">“{q.text}”</p>
                          {q.reason && <p className="text-[var(--text-muted)] mt-0.5 italic">{q.reason}</p>}
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            );
          })()}
        </div>
      )}

      {/* New brief */}
      {brief && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-[var(--text)]">Annotated brief</h2>
              <p className="text-xs font-mono text-[var(--text-muted)] mt-1">{brief.name}</p>
            </div>
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white bg-[var(--primary)] hover:opacity-90 transition-colors"
            >
              <Download className="w-4 h-4" />
              Download
            </button>
          </div>
          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-[var(--text-dim)] max-h-96 overflow-y-auto p-4 rounded-lg" style={{ background: 'var(--surface2)' }}>
            {brief.content}
          </pre>
        </div>
      )}
    </div>
  );
}
