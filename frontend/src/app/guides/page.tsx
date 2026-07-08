'use client';

import { useState } from 'react';
import { FileText, Search, Shield, Target, BarChart3, Globe, Briefcase, BookOpen, FileCheck, X } from 'lucide-react';

interface Guide {
  title: string;
  file: string;
  desc: string;
  icon: typeof FileText;
  category: 'System' | 'Matter Intake' | 'Contract Review' | 'Employment' | 'Due Diligence' | 'Regulatory' | 'KM' | 'Reporting' | 'Governance';
}

const GUIDES: Guide[] = [
  {
    title: 'How It Works',
    file: 'how-it-works.html',
    desc: 'Top-level architecture showing how all seven functions connect — front door, deep work, and intelligence layers.',
    icon: Target,
    category: 'System',
  },
  {
    title: 'Platform Overview',
    file: 'legal-ai-os-overview.html',
    desc: 'Five-layer operating model for enterprise legal AI — governance architecture, specialized functions, and the operational layer that connects them.',
    icon: Target,
    category: 'System',
  },
  {
    title: 'Governance Architecture',
    file: 'legal-ai-governance.html',
    desc: 'How the Legal AI OS enforces auditability, explainability, and traceability across every function and decision.',
    icon: Shield,
    category: 'Governance',
  },
  {
    title: 'Technical Architecture',
    file: 'legal-ai-technical-architecture.html',
    desc: 'Storage architecture options, deployment topology, and integration patterns for enterprise legal AI.',
    icon: BarChart3,
    category: 'System',
  },
  {
    title: 'Matter Intake Overview',
    file: 'matter-intake-overview.html',
    desc: 'End-to-end matter intake flow — from initial contact through triage, conflict check, and routing.',
    icon: Search,
    category: 'Matter Intake',
  },
  {
    title: 'Matter Intake Pipeline',
    file: 'matter-intake-pipeline.html',
    desc: 'Detailed pipeline view — classification, urgency scoring, resource matching, and audit trail.',
    icon: Search,
    category: 'Matter Intake',
  },
  {
    title: 'Contract Review Showcase',
    file: 'contract-review-showcase.html',
    desc: 'Structured risk analysis with clause-level flagging, playbook-driven review, and HITL workflow.',
    icon: FileText,
    category: 'Contract Review',
  },
  {
    title: 'Employment Overview',
    file: 'employment-overview.html',
    desc: 'Worker classification, FLSA compliance, and handbook audit — five-step pipeline with governance artifacts.',
    icon: Briefcase,
    category: 'Employment',
  },
  {
    title: 'Regulatory Monitor',
    file: 'regulatory-monitor.html',
    desc: 'Multi-source polling across federal, state, and agency feeds with impact-classified change detection.',
    icon: Globe,
    category: 'Regulatory',
  },
  {
    title: 'KM & Precedent Intelligence',
    file: 'km-intelligence.html',
    desc: 'Semantic search, precedent linking, and knowledge graph — connecting all firm documents with citations.',
    icon: BookOpen,
    category: 'KM',
  },
  {
    title: 'Client Value Reporting',
    file: 'value-reporting.html',
    desc: 'Quarterly per-client reports — time saved per function, risk metrics, governance artifacts, and YoY trends.',
    icon: FileCheck,
    category: 'Reporting',
  },
];

export default function GuidesPage() {
  const categories = [...new Set(GUIDES.map((g) => g.category))];
  const [selected, setSelected] = useState<Guide | null>(null);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] mt-3 mb-2">
            Guides & Diagrams
          </h1>
          <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
            Visual explainers showing how each function works, the governance
            architecture, and the technical infrastructure behind the platform.
          </p>
        </div>
        {selected && (
          <button
            onClick={() => setSelected(null)}
            className="btn-secondary flex items-center gap-2"
          >
            <X className="w-4 h-4" />
            Close
          </button>
        )}
      </div>

      {/* Embedded viewer */}
      {selected && (
        <div className="card overflow-hidden mb-6" style={{ minHeight: 'calc(100vh - 340px)' }}>
          <iframe
            src={`/guides/${selected.file}`}
            className="w-full border-0"
            style={{ minHeight: 'calc(100vh - 340px)' }}
            title={selected.title}
          />
        </div>
      )}

      {/* Guide cards */}
      {!selected && categories.map((cat) => {
        const items = GUIDES.filter((g) => g.category === cat);
        return (
          <section key={cat} className="mb-8">
            <h2 className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-3">
              {cat}
            </h2>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {items.map((g) => {
                const Icon = g.icon;
                return (
                  <button
                    key={g.file}
                    onClick={() => setSelected(g)}
                    className="card p-5 text-left hover:border-[var(--primary)] group cursor-pointer flex-shrink-0"
                    style={{ width: '280px' }}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className="w-4 h-4 text-[var(--primary)]" />
                      <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                        {g.category}
                      </span>
                    </div>
                    <h3 className="font-semibold text-[15px] mb-1 text-[var(--text)] group-hover:text-[var(--primary)] transition-colors">
                      {g.title}
                    </h3>
                    <p className="text-[13px] text-[var(--text-dim)] leading-relaxed">
                      {g.desc}
                    </p>
                  </button>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
