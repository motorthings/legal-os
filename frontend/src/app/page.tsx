import Link from "next/link";

const FUNCTIONS = [
  {
    slug: "matter-intake",
    name: "Matter Intake & Triage",
    desc: "Structured evaluation of new matters in under 10 seconds.",
    status: "built",
  },
  {
    slug: "contract-review",
    name: "Contract Review & Analysis",
    desc: "Structured risk analysis with clause-level flagging and HITL review.",
    status: "built",
  },
  {
    slug: "employment-agents",
    name: "Employment Legal Agents",
    desc: "AI agents for employment law — policy review, compliance, classification.",
    status: "built",
  },
  {
    slug: "cowork-legal-plugin",
    name: "Cowork Legal Plugin",
    desc: "Legal AI plugin for the Cowork knowledge work platform.",
    status: "built",
  },
  {
    slug: "due-diligence",
    name: "Due Diligence Accelerator",
    desc: "Bulk document ingestion, target standards, deviation-only reporting.",
    status: "roadmap",
    href: "/due-diligence",
    enabled: true,
  },
  {
    slug: "regulatory-monitor",
    name: "Regulatory Change Monitor",
    desc: "Poll regulatory sources, map changes to active matters by jurisdiction.",
    status: "roadmap",
    href: "/regulatory",
    enabled: true,
  },
  {
    slug: "km-intelligence",
    name: "KM & Precedent Intelligence",
    desc: "Semantic search across all firm documents with citations.",
    status: "roadmap",
    href: "/km",
    enabled: true,
  },
  {
    slug: "client-value-reporting",
    name: "Client Value Reporting",
    desc: "Per-client quarterly reports — time saved, risk, governance artifacts.",
    status: "roadmap",
    href: "/reporting",
    enabled: true,
  },
];

export default function Home() {
  return (
    <div>
      {/* Hero */}
      <header className="mb-10">
        <div className="inline-block mb-3">
          <span className="badge badge-built text-xs">Platform</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-[var(--text)] mb-3">
          Legal AI Operating System
        </h1>
        <p className="font-mono text-sm text-[var(--text-dim)] max-w-xl">
          Eight functions. One governance layer. Every decision auditable,
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
        Eight Functions
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
              <span
                className={`badge ${
                  fn.status === "built" ? "badge-built" : "badge-roadmap"
                }`}
              >
                {fn.status}
              </span>
            </div>
            <h3 className="font-semibold text-[15px] mb-1">{fn.name}</h3>
            <p className="text-[13px] text-[var(--text-dim)] leading-relaxed">
              {fn.desc}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
