'use client';

import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function UserMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const { user, profile, signOut } = useAuth();
  const router = useRouter();
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleSignOut = async () => {
    await signOut();
    router.push('/auth/login');
  };

  const isAdmin = profile?.role === 'admin';

  return (
    <div className="relative" ref={menuRef}>
      {/* User Avatar/Menu Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-hover transition-colors focus-ring"
        aria-label="User menu"
        aria-expanded={isOpen}
      >
        {/* Avatar */}
        {profile?.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt={profile?.name || 'User'}
            className="w-10 h-10 rounded-full object-cover border-2 border-default"
          />
        ) : (
          <div className="avatar-primary w-10 h-10 text-base">
            {profile?.name ? profile.name.charAt(0).toUpperCase() : '?'}
          </div>
        )}

        {/* Dropdown icon */}
        <svg
          className={`w-4 h-4 icon-muted transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 bg-card border border-default rounded-lg shadow-card-hover overflow-hidden z-50">
          {/* User Info Section */}
          <div className="px-3 py-2 bg-hover border-b border-default">
            <div className="flex items-center gap-2">
              {/* Avatar in dropdown */}
              {profile?.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt={profile?.name || 'User'}
                  className="w-10 h-10 rounded-full object-cover border-2 border-default flex-shrink-0"
                />
              ) : (
                <div className="avatar-primary w-10 h-10 text-base flex-shrink-0">
                  {profile?.name ? profile.name.charAt(0).toUpperCase() : '?'}
                </div>
              )}
              <div className="flex-1">
                <p className="text-sm font-medium text-primary whitespace-nowrap">
                  {profile?.name || 'User'}
                </p>
                <p className="text-xs text-muted whitespace-nowrap">
                  {user?.email}
                </p>
              </div>
            </div>
            {profile?.role && (
              <span className="badge-primary capitalize text-xs mt-1.5 inline-block">
                {profile.role.replace('_', ' ')}
              </span>
            )}
          </div>

          {/* Menu Items */}
          <div className="py-1">
            {/* Profile Link */}
            <Link
              href="/profile"
              className="flex items-center w-full px-3 py-2 text-sm hover:bg-hover transition-colors text-primary"
              onClick={() => setIsOpen(false)}
            >
              <svg className="w-4 h-4 mr-2 icon-muted flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span className="whitespace-nowrap">Profile Settings</span>
            </Link>

            {/* Chat Link - Only for non-admin users (client users) */}
            {!isAdmin && (
              <Link
                href="/chat"
                className="flex items-center w-full px-3 py-2 text-sm hover:bg-hover transition-colors text-primary"
                onClick={() => setIsOpen(false)}
              >
                <svg className="w-4 h-4 mr-2 icon-muted flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span className="whitespace-nowrap">Chat</span>
              </Link>
            )}

            {/* Divider */}
            <div className="my-1 border-t border-border"></div>

            {/* Sign Out */}
            <button
              onClick={handleSignOut}
              className="w-full flex items-center px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
            >
              <svg className="w-4 h-4 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              <span className="whitespace-nowrap">Sign Out</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
