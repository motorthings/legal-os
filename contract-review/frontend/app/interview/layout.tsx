'use client';

import SecurityFooter from '@/components/SecurityFooter';

export default function InterviewLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-page">
      <main className="flex-1">
        {children}
      </main>
      <SecurityFooter />
    </div>
  );
}
