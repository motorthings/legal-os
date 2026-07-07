'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import ChatInterface from './ChatInterface'
import ConversationSidebar from './ConversationSidebar'
import Link from 'next/link'

interface UnifiedWorkspaceProps {
  clientId?: string  // Optional - backend auto-assigns default client
  userId: string
  conversationId?: string
}

export default function UnifiedWorkspace({
  clientId,
  userId,
  conversationId
}: UnifiedWorkspaceProps) {
  const { user, profile, signOut } = useAuth()
  const router = useRouter()

  const [selectedPromptText, setSelectedPromptText] = useState<string | null>(null)
  const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0)
  const [menuOpen, setMenuOpen] = useState(false)

  // User menu helpers
  const isAdmin = profile?.role === 'admin'
  const getInitials = (name?: string | null) => {
    if (!name) return '?'
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  const handleSignOut = async () => {
    await signOut()
    router.push('/auth/login')
  }

  const handlePromptSelect = (promptText: string) => {
    setSelectedPromptText(promptText)
  }

  const handleConversationCreated = () => {
    // Trigger sidebar refresh when a new conversation is created
    setSidebarRefreshTrigger(prev => prev + 1)
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Top Header Bar - Desktop and Mobile */}
      <div className="bg-card flex items-center justify-between px-4 py-3 border-b border-default flex-shrink-0 relative">
        {/* Hamburger Menu and Profile Avatar */}
        <div className="relative flex items-center gap-3">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="p-2 hover:bg-hover rounded-md transition-colors"
            aria-label="Menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* Profile Avatar (display only) */}
          {profile?.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt={profile?.name || 'User'}
              className="w-9 h-9 rounded-full object-cover"
            />
          ) : (
            <div className="w-9 h-9 rounded-full bg-brand flex items-center justify-center">
              <span className="text-white text-sm font-semibold">
                {getInitials(profile?.name)}
              </span>
            </div>
          )}

          {/* Dropdown Menu */}
          {menuOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setMenuOpen(false)}
              />
              <div className="absolute left-0 top-full mt-2 w-64 bg-card border border-default rounded-lg shadow-lg z-20">
                {/* User Info Section */}
                <div className="px-4 py-4 border-b border-default">
                  <div className="flex items-center gap-3 mb-2">
                    {profile?.avatar_url ? (
                      <img
                        src={profile.avatar_url}
                        alt={profile?.name || 'User'}
                        className="w-12 h-12 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-brand flex items-center justify-center flex-shrink-0">
                        <span className="text-white text-lg font-semibold">
                          {getInitials(profile?.name)}
                        </span>
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-primary truncate">
                        {profile?.name || 'User'}
                      </div>
                      <div className="text-xs text-secondary truncate">
                        {user?.email}
                      </div>
                    </div>
                  </div>
                  {profile?.role && (
                    <div className="inline-flex items-center px-2 py-1 rounded-md bg-accent text-xs font-medium text-brand capitalize">
                      {profile.role}
                    </div>
                  )}
                </div>

                {/* Navigation Section */}
                <div className="py-1">
                  <Link href="/documents" onClick={() => setMenuOpen(false)}>
                    <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                      <span className="text-sm text-primary">Documents</span>
                    </div>
                  </Link>
                </div>

                <div className="border-t border-default"></div>

                {/* Profile & Settings */}
                <div className="py-1">
                  <Link href="/profile" onClick={() => setMenuOpen(false)}>
                    <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                      <span className="text-sm text-primary">Profile Settings</span>
                    </div>
                  </Link>
                </div>

                {/* Admin Links */}
                {isAdmin && (
                  <>
                    <div className="border-t border-default"></div>
                    <div className="py-1">
                      <Link href="/admin/users" onClick={() => setMenuOpen(false)}>
                        <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                          <span className="text-sm text-primary">Users</span>
                        </div>
                      </Link>
                      <Link href="/admin/conversations" onClick={() => setMenuOpen(false)}>
                        <div className="px-4 py-2 hover:bg-hover cursor-pointer transition-colors">
                          <span className="text-sm text-primary">Conversations</span>
                        </div>
                      </Link>
                    </div>
                  </>
                )}

                <div className="border-t border-default"></div>

                {/* Sign Out */}
                <div className="py-1">
                  <button
                    onClick={handleSignOut}
                    className="w-full text-left px-4 py-2 hover:bg-hover cursor-pointer transition-colors"
                  >
                    <span className="text-sm text-red-600">Sign Out</span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Centered Title */}
        <div className="absolute left-1/2 transform -translate-x-1/2">
          <h1 className="text-2xl font-semibold text-brand">Contract Review</h1>
        </div>

        {/* Empty right side for balance */}
        <div className="w-9"></div>
      </div>

      {/* Main Workspace - 2-column layout */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left Sidebar - Conversations */}
        <div className="w-80 border-r border-gray-200 h-full overflow-hidden">
          <ConversationSidebar
            clientId={clientId}
            userId={userId}
            currentConversationId={conversationId}
            onPromptSelect={handlePromptSelect}
            refreshTrigger={sidebarRefreshTrigger}
            className="h-full"
          />
        </div>

        {/* Right - Chat Interface */}
        <div className="flex-1 h-full overflow-hidden">
          <ChatInterface
            clientId={clientId}
            userId={userId}
            conversationId={conversationId}
            initialPromptText={selectedPromptText}
            onPromptUsed={() => setSelectedPromptText(null)}
            onConversationCreated={handleConversationCreated}
          />
        </div>
      </div>
    </div>
  )
}
