'use client'

import LazyUnifiedWorkspace from '@/components/LazyUnifiedWorkspace'
import LoadingSpinner from '@/components/LoadingSpinner'
import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

function ChatPageContent() {
  const { user, profile, loading } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const conversationId = searchParams.get('id') || undefined
  const timestamp = searchParams.get('t') || undefined

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!loading && !user) {
      router.push('/auth/login')
    }
  }, [loading, user, router])

  // Show loading state while auth is being checked
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-page">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="text-secondary mt-4">Loading your workspace...</p>
        </div>
      </div>
    )
  }

  // Show error if no profile
  if (!profile) {
    return (
      <div className="flex items-center justify-center h-screen bg-page">
        <div className="text-center max-w-md">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-red-800 mb-2">Account Setup Incomplete</h2>
            <p className="text-red-700 mb-4">
              Unable to load your profile. Please try logging in again.
            </p>
            <button
              onClick={() => router.push('/auth/login')}
              className="btn-primary px-4 py-2"
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <LazyUnifiedWorkspace
      key={conversationId || timestamp || 'new'}
      clientId={profile.client_id}  // Optional - auto-assigned by backend
      userId={user!.id}
      conversationId={conversationId}
    />
  )
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-screen">Loading...</div>}>
      <ChatPageContent />
    </Suspense>
  )
}
