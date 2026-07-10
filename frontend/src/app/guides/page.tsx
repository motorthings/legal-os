'use client';

import { useState } from 'react';
import Link from 'next/link';
import { FileText, Search, Shield, Target, BarChart3, Globe, Briefcase, BookOpen, FileCheck, ChevronRight, GraduationCap } from 'lucide-react';

interface Guide {
  title: string;
  slug: string;
  desc: string;
  icon: typeof FileText;
  category: string;
}

const GUIDES: Guide[] = [
  {
    title: 'How It Works',
    slug: 'how-it-works',
    desc: 'Top-level architecture showing how all seven functions connect — front door, deep work, and intelligence layers.',
    icon: Target,
    category: 'System',
  },
  {
    title: 'Platform Overview',
    slug: 'platform-overview',
    desc: 'Five-layer operating model for enterprise legal AI — governance architecture, specialized functions, and the operational layer that connects them.',
    icon: Target,
    category: 'System',
  },
  {
    title: 'Governance Architecture',
    slug: 'governance-architecture',
    desc: 'How the Legal AI OS enforces auditability, explainability, and traceability across every function and decision.',
    icon: Shield,
    category: 'Governance',
  },
  {
    title: 'Technical Architecture',
    slug: 'technical-architecture',
    desc: 'Storage architecture options, deployment topology, and integration patterns for enterprise legal AI.',
    icon: BarChart3,
    category: 'System',
  },
  {
    title: 'Matter Intake Overview',
    slug: 'matter-intake-overview',
    desc: 'End-to-end matter intake flow — from initial contact through triage, conflict check, and routing.',
    icon: Search,
    category: 'Matter Intake',
  },
  {
    title: 'Matter Intake Pipeline',
    slug: 'matter-intake-pipeline',
    desc: 'Detailed pipeline view — classification, urgency scoring, resource matching, and audit trail.',
    icon: Search,
    category: 'Matter Intake',
  },
  {
    title: 'Contract Review Showcase',
    slug: 'contract-review-showcase',
    desc: 'Structured risk analysis with clause-level flagging, playbook-driven review, and HITL workflow.',
    icon: FileText,
    category: 'Contract Review',
  },
  {
    title: 'Employment Overview',
    slug: 'employment-overview',
    desc: 'Worker classification, FLSA compliance, and handbook audit — five-step pipeline with governance artifacts.',
    icon: Briefcase,
    category: 'Employment',
  },
  {
    title: 'Regulatory Monitor',
    slug: 'regulatory-monitor',
    desc: 'Multi-source polling across federal, state, and agency feeds with impact-classified change detection.',
    icon: Globe,
    category: 'Regulatory',
  },
  {
    title: 'KM & Precedent Intelligence',
    slug: 'km-intelligence',
    desc: 'Semantic search, precedent linking, and knowledge graph — connecting all firm documents with citations.',
    icon: BookOpen,
    category: 'KM',
  },
  {
    title: 'Client Value Reporting',
    slug: 'value-reporting',
    desc: 'Quarterly per-client reports — time saved per function, risk metrics, governance artifacts, and YoY trends.',
    icon: FileCheck,
    category: 'Reporting',
  },
  {
    title: 'Enablement Kit',
    slug: 'enablement-kit',
    desc: 'AI literacy workshop, prompt engineering guide, adoption playbook, lawyer FAQ, client conversation pack, and RFP templates.',
    icon: GraduationCap,
    category: 'Operations',
  },
];

const CATEGORIES = [...new Set(GUIDES.map((g) => g.category))];

export default function GuidesPage() {
  const [open, setOpen] = useState<Set<string>>(new Set());

  const toggle = (cat: string) => {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-4xl font-bold tracking-tight text-[var(--text)] mt-3 mb-2">
          Guides & Diagrams
        </h1>
        <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
          Visual explainers showing how each function works, the governance
          architecture, and the technical infrastructure behind the platform.
        </p>
      </header>

      <div className="flex flex-col gap-2">
        {CATEGORIES.map((cat) => {
          const items = GUIDES.filter((g) => g.category === cat);
          const isOpen = open.has(cat);
          return (
            <div key={cat}>
              <button
                onClick={() => toggle(cat)}
                className="w-full flex items-center gap-2 py-2 text-left group"
              >
                <ChevronRight
                  className="w-4 h-4 text-[var(--text-muted)] transition-transform flex-shrink-0"
                  style={{ transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}
                />
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)] group-hover:text-[var(--text)] transition-colors">
                  {cat}
                </span>
                <span className="text-[10px] text-[var(--text-muted)] font-mono">({items.length})</span>
              </button>
              {isOpen && (
                <div className="flex flex-col gap-2 ml-2 mb-3">
                  {items.map((g) => {
                    const Icon = g.icon;
                    return (
                      <Link
                        key={g.slug}
                        href={`/guides/${g.slug}`}
                        className="card p-4 text-left hover:border-[var(--primary)] group cursor-pointer no-underline w-full block"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <Icon className="w-4 h-4 text-[var(--primary)]" />
                          <h3 className="font-semibold text-[15px] text-[var(--text)] group-hover:text-[var(--primary)] transition-colors">
                            {g.title}
                          </h3>
                        </div>
                        <p className="text-[13px] text-[var(--text-dim)] leading-relaxed">
                          {g.desc}
                        </p>
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
