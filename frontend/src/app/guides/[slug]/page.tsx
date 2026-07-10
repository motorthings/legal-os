import { GuidePageClient } from "./client";

const SLUG_TO_FILE: Record<string, string> = {
  "how-it-works": "how-it-works.html",
  "platform-overview": "legal-ai-os-overview.html",
  "governance-architecture": "legal-ai-governance.html",
  "technical-architecture": "legal-ai-technical-architecture.html",
  "matter-intake-overview": "matter-intake-overview.html",
  "matter-intake-pipeline": "matter-intake-pipeline.html",
  "contract-review-showcase": "contract-review-showcase.html",
  "employment-overview": "employment-overview.html",
  "regulatory-monitor": "regulatory-monitor.html",
  "km-intelligence": "km-intelligence.html",
  "value-reporting": "value-reporting.html",
  "enablement-kit": "enablement-kit.html",
};

export async function generateStaticParams() {
  return Object.keys(SLUG_TO_FILE).map((slug) => ({ slug }));
}

export default async function GuidePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const file = SLUG_TO_FILE[slug];
  return <GuidePageClient slug={slug} file={file} />;
}
