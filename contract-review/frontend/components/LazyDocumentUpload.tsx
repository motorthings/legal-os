'use client';

import dynamic from 'next/dynamic';
import LoadingSpinner from './LoadingSpinner';

// Lazy load DocumentUpload to reduce initial bundle
const DocumentUpload = dynamic(() => import('./DocumentUpload'), {
  loading: () => (
    <div className="flex items-center justify-center p-8">
      <LoadingSpinner size="lg" />
    </div>
  ),
  ssr: false,
});

export default function LazyDocumentUpload(props: any) {
  return <DocumentUpload {...props} />;
}
