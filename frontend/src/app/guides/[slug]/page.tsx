import { GuidePageClient } from "./client";

// Diagrams are canonical in the motorthings/diagrams portfolio and iframed from there;
// user-facing guides stay local to the app.
const DIAGRAMS_BASE = "/api/guides/legal";

const SLUG_TO_TARGET: Record<string, string> = {
  // Diagrams — external (iframe the diagrams repo page)
  "platform-overview": `${DIAGRAMS_BASE}/legal-ai-os-overview.html`,
  "governance-architecture": `${DIAGRAMS_BASE}/legal-ai-governance.html`,
  "technical-architecture": `${DIAGRAMS_BASE}/legal-ai-storage-architecture-diagrams.html`,
  "matter-intake-overview": `${DIAGRAMS_BASE}/matter-intake-overview.html`,
  "matter-intake-pipeline": `${DIAGRAMS_BASE}/matter-intake-pipeline.html`,
  "nlp-preprocessing": `${DIAGRAMS_BASE}/legal-os-nlp-preprocessing.html`,
  // Guides — local to the app
  "how-it-works": "how-it-works.html",
  "contract-review-showcase": "contract-review-showcase.html",
  "employment-overview": "employment-overview.html",
  "regulatory-monitor": "regulatory-monitor.html",
  "km-intelligence": "km-intelligence.html",
  "value-reporting": "value-reporting.html",
  "enablement-kit": "enablement-kit.html",
  "legal-research": "legal-research.html",
  "cite-check": "cite-check.html",
};

export async function generateStaticParams() {
  return Object.keys(SLUG_TO_TARGET).map((slug) => ({ slug }));
}

export default async function GuidePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const target = SLUG_TO_TARGET[slug];
  const external = (target?.startsWith("http") || target?.startsWith("/api/")) ?? false;
  return (
    <GuidePageClient
      slug={slug}
      file={external ? undefined : target}
      url={external ? target : undefined}
    />
  );
}
