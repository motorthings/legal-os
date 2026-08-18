import Link from "next/link";

const FUNCTIONS = [
  {
    slug: "matter-intake",
    name: "Matter Intake & Triage",
    desc: "Structured evaluation of new matters in under 10 seconds.",
    status: "built",
    href: "/matter-intake",
    enabled: true,
  },
  {
    slug: "contract-review",
    name: "Contract Review & Analysis",
    desc: "Structured risk analysis with clause-level flagging and HITL review.",
    status: "built",
    href: "/contract-review",
    enabled: true,
  },
  {
    slug: "employment-agents",
    name: "Employment Legal Agents",
    desc: "AI agents for employment law — policy review, compliance, classification.",
    status: "built",
    href: "/employment",
    enabled: true,
  },
  {
    slug: "due-diligence",
    name: "Due Diligence Accelerator",
    desc: "Bulk document ingestion, target standards, deviation-only reporting.",
    status: "built",
    href: "/due-diligence",
    enabled: true,
  },
  {
    slug: "regulatory-monitor",
    name: "Regulatory Change Monitor",
    desc: "Poll regulatory sources, map changes to active matters by jurisdiction.",
    status: "built",
    href: "/regulatory",
    enabled: true,
  },
  {
    slug: "legal-research",
    name: "Legal Research",
    desc: "Descrybe-powered case law, statutes, and citation intelligence — good-law treatment, authority ranking, and quote verification.",
    status: "built",
    href: "/legal-research",
    enabled: true,
  },
  {
    slug: "cite-check",
    name: "Cite Check",
    desc: "Validate a brief against Descrybe before filing — citations confirmed, quotes verified word-for-word.",
    status: "built",
    href: "/cite-check",
    enabled: true,
  },
  {
    slug: "km-intelligence",
    name: "KM & Precedent Intelligence",
    desc: "Semantic search across all firm documents with citations.",
    status: "built",
    href: "/km",
    enabled: true,
  },
  {
    slug: "client-value-reporting",
    name: "Client Value Reporting",
    desc: "Per-client quarterly reports — time saved, risk, governance artifacts.",
    status: "built",
    href: "/reporting",
    enabled: true,
  },
  {
    slug: "firm-simulation",
    name: "Firm Simulation",
    desc: "Monte-Carlo digital twin of your firm's economics — model where value leaks and which levers move profit.",
    status: "built",
    href: "/simulation",
    enabled: true,
  },
];

export default function Home() {
  return (
    <div>
      {/* Hero */}
      <header className="mb-10">
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-[var(--text)] mb-3">
          Legal AI Operating System
        </h1>
        <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
          Ten functions. One governance layer. Every decision auditable,
          explainable, and traceable &mdash; by design.
        </p>
      </header>

      {/* Governance pillars */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-10">
        {[
          { label: "Auditability", desc: "Full prompt capture, score replay, immutable" },
          { label: "Explainability", desc: "Chain of reasoning, source attribution, visible" },
          { label: "Traceability", desc: "Who, when, what, why — every override logged" },
        ].map((p) => (
          <div key={p.label} className="card p-5">
            <h3 className="font-semibold text-base mb-1">{p.label}</h3>
            <p className="text-sm text-[var(--text-dim)]">{p.desc}</p>
          </div>
        ))}
      </div>

      {/* Functions grid */}
      <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--text-dim)] mb-4">
        Ten Functions
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {FUNCTIONS.map((fn) => (
          <Link
            key={fn.slug}
            href={(fn as any).href || `#${fn.slug}`}
            className={`card p-5 no-underline ${
              (fn as any).enabled
                ? "hover:border-[var(--primary)]"
                : "opacity-60 pointer-events-none"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                {fn.slug}
              </span>
            </div>
            <h3 className="font-semibold text-[15px] mb-1">{fn.name}</h3>
            <p className="text-[13px] text-[var(--text-dim)] leading-relaxed">
              {fn.desc}
            </p>
          </Link>
        ))}
      </div>

      {/* Knowledge Foundation */}
      <h2 className="font-mono text-xs font-semibold uppercase tracking-widest text-[var(--text-dim)] mb-4 mt-10">
        Knowledge Foundation
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {[
          { name: "Embeddings", desc: "Voyage AI (voyage-3-large, 1024-dim) with pgvector cosine search for semantic retrieval." },
          { name: "Knowledge Base & RAG", desc: "Chunked document ingestion, embedding generation, and similarity retrieval across the firm's corpus." },
          { name: "NLP & Text Pipeline", desc: "Normalization and chunking that prepare documents and queries for retrieval." },
        ].map((k) => (
          <div key={k.name} className="card p-5">
            <h3 className="font-semibold text-[15px] mb-1">{k.name}</h3>
            <p className="text-[13px] text-[var(--text-dim)] leading-relaxed">{k.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
