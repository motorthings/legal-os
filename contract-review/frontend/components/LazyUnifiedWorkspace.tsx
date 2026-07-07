'use client';

import dynamic from 'next/dynamic';
import LoadingSpinner from './LoadingSpinner';

// Lazy load UnifiedWorkspace to reduce initial bundle
// This includes ChatInterface, markdown rendering, syntax highlighting, and more
const UnifiedWorkspace = dynamic(() => import('./UnifiedWorkspace'), {
  loading: () => (
    <div className="flex items-center justify-center h-screen bg-page">
      <div className="text-center">
        <LoadingSpinner size="lg" />
        <p className="text-secondary mt-4">Loading your workspace...</p>
      </div>
    </div>
  ),
  ssr: false,
});

export default function LazyUnifiedWorkspace(props: any) {
  return <UnifiedWorkspace {...props} />;
}
