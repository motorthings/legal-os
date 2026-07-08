import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import ThemeToggle from "@/components/ThemeToggle";
import ThemeInit from "@/components/ThemeInit";

export const metadata: Metadata = {
  title: "Legal AI OS",
  description:
    "A governed platform for building, deploying, and measuring AI across the legal enterprise. Eight functions. One governance layer.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                if (localStorage.getItem('legal-os-theme') === 'dark' ||
                    (!localStorage.getItem('legal-os-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                  document.documentElement.classList.add('dark');
                }
              } catch(e) {}
            `,
          }}
        />
      </head>
      <body className="min-h-screen pb-12">
        <nav className="nav-blur sticky top-0 z-50 px-4 sm:px-8">
          <div className="max-w-6xl mx-auto py-3 flex items-center justify-between">
            <Link
              href="/"
              className="font-mono text-xs font-semibold tracking-wider text-[var(--primary)] no-underline"
            >
              LEGAL AI OS
            </Link>
            <div className="flex items-center gap-4">
              <Link
                href="/due-diligence"
                className="font-mono text-xs text-[var(--text-dim)] hover:text-[var(--secondary)] no-underline transition-colors"
              >
                Due Diligence
              </Link>
              <ThemeToggle />
            </div>
          </div>
        </nav>
        <ThemeInit />
        <main className="max-w-6xl mx-auto px-4 sm:px-8 pt-8">{children}</main>
      </body>
    </html>
  );
}
