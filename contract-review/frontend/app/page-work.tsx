'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import LoadingSpinner from '@/components/LoadingSpinner';

export default function Home() {
  const router = useRouter();
  const { user, profile, loading } = useAuth();

  useEffect(() => {
    if (!loading) {
      if (!user) {
        // Not authenticated - redirect to login
        router.push('/auth/login');
      } else if (profile?.role === 'admin') {
        // Admin users - redirect to admin dashboard
        router.push('/admin');
      } else {
        // Regular users - redirect to contracts dashboard
        router.push('/contracts');
      }
    }
  }, [user, profile, loading, router]);

  // Show loading state while checking authentication
  return (
    <div className="min-h-screen bg-page flex items-center justify-center">
      <div className="text-center">
        <div className="mb-4">
          <h1 className="text-2xl font-semibold text-brand mb-2">Contract Review</h1>
          <p className="text-muted">Loading...</p>
        </div>
        <LoadingSpinner size="lg" />
      </div>
    </div>
  );
}
