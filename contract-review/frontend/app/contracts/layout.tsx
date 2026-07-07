'use client';

import SecurityFooter from '@/components/SecurityFooter';

export default function ContractsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-page">
      <main className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4 pb-8 flex-1">
        {children}
      </main>
      <SecurityFooter />
    </div>
  );
}
