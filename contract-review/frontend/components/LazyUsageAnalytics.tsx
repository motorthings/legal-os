'use client';

import dynamic from 'next/dynamic';
import LoadingSpinner from './LoadingSpinner';

// Lazy load UsageAnalytics component with recharts
// This reduces initial bundle size by ~100-150KB
const UsageAnalytics = dynamic(() => import('./UsageAnalytics'), {
  loading: () => (
    <div className="flex items-center justify-center p-8">
      <LoadingSpinner size="lg" />
    </div>
  ),
  ssr: false, // Disable SSR for this component as charts don't need server rendering
});

export default function LazyUsageAnalytics(props: any) {
  return <UsageAnalytics {...props} />;
}
