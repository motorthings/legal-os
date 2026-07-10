"use client";

import { useRef, useEffect, useCallback, useState } from "react";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";

function buildThemeCSS(): string {
  if (typeof document === "undefined") return "";
  const style = getComputedStyle(document.documentElement);
  const get = (name: string) => style.getPropertyValue(name).trim();
  if (!get("--bg")) return "";
  return `
@media all {
  :root {
    --bg: ${get("--bg")} !important;
    --surface: ${get("--surface")} !important;
    --surface2: ${get("--surface2")} !important;
    --border: ${get("--border")} !important;
    --border-bright: ${get("--border-bright")} !important;
    --text: ${get("--text")} !important;
    --text-dim: ${get("--text-dim")} !important;
    --text-muted: ${get("--text-muted")} !important;
    --primary: ${get("--primary")} !important;
    --primary-dim: ${get("--primary-dim")} !important;
    --secondary: ${get("--secondary")} !important;
    --secondary-dim: ${get("--secondary-dim")} !important;
    --metric: ${get("--metric")} !important;
    --metric-dim: ${get("--metric-dim")} !important;
    --rose: ${get("--rose")} !important;
    --violet: ${get("--violet")} !important;
    --amber: ${get("--amber")} !important;
  }
}
`;
}

export function GuidePageClient({ slug, file }: { slug: string; file: string | undefined }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [ready, setReady] = useState(false);

  const applyTheme = useCallback(() => {
    const doc = iframeRef.current?.contentDocument;
    if (!doc) return;
    let style = doc.getElementById("legal-os-theme-override") as HTMLStyleElement | null;
    if (!style) {
      style = doc.createElement("style");
      style.id = "legal-os-theme-override";
      doc.head.appendChild(style);
    }
    style.textContent = buildThemeCSS();
  }, []);

  const handleLoad = useCallback(() => {
    applyTheme();
    setReady(true);
  }, [applyTheme]);

  useEffect(() => {
    applyTheme();
  }, [applyTheme]);

  useEffect(() => {
    const observer = new MutationObserver(() => applyTheme());
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, [applyTheme]);

  if (!file) {
    return (
      <div>
        <Link href="/guides" className="inline-flex items-center gap-1 text-sm text-[var(--text-dim)] hover:text-[var(--text)] transition-colors mb-6 no-underline">
          <ChevronLeft className="w-4 h-4" />
          Guides & Diagrams
        </Link>
        <h1 className="text-3xl font-bold text-[var(--text)]">Guide not found</h1>
      </div>
    );
  }

  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
      {/* Spinner */}
      {!ready && (
        <div className="flex items-center justify-center" style={{ height: "100%" }}>
          <div className="w-5 h-5 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Iframe — fills the entire main area */}
      <iframe
        ref={iframeRef}
        src={`/guides/${file}`}
        title={slug}
        onLoad={handleLoad}
        style={{
          width: "100%",
          height: "100%",
          border: "none",
          display: ready ? "block" : "none",
        }}
      />
    </div>
  );
}
