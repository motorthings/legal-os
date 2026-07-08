import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import ThemeToggle from "@/components/ThemeToggle";
import ThemeInit from "@/components/ThemeInit";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Legal AI OS",
  description:
    "A governed platform for building, deploying, and measuring AI across the legal enterprise. Seven functions. One governance layer.",
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
      <body className="min-h-screen">
        <AuthProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 min-w-0 overflow-y-auto relative">
              <div className="fixed top-4 right-4 z-50">
                <ThemeToggle />
              </div>
              <div className="max-w-6xl mx-auto px-4 sm:px-8 pt-8 pb-12">
                {children}
              </div>
            </main>
          </div>
        </AuthProvider>
        <ThemeInit />
      </body>
    </html>
  );
}
