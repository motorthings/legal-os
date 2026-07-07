'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import UserMenu from '@/components/UserMenu';
import LoadingSpinner from '@/components/LoadingSpinner';
import SecurityFooter from '@/components/SecurityFooter';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, profile, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  // Check admin access
  useEffect(() => {
    if (!loading) {
      // Not logged in - redirect to login
      if (!user) {
        router.push('/auth/login');
        return;
      }

      // Logged in but not admin - redirect to contracts
      if (profile && profile.role !== 'admin') {
        router.push('/contracts');
        return;
      }
    }
  }, [loading, user, profile, router]);

  // Show loading state while checking auth
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-page">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="text-muted mt-4">Loading...</p>
        </div>
      </div>
    );
  }

  // Show loading state while redirecting non-admin users
  if (!user || (profile && profile.role !== 'admin')) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-page">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="text-muted mt-4">Redirecting...</p>
        </div>
      </div>
    );
  }

  const navLinks = [
    { href: '/admin', label: 'Dashboard' },
    { href: '/admin/contracts', label: 'Contracts' },
    { href: '/admin/legal-standards', label: 'Legal Standards' },
    { href: '/admin/settings', label: 'Settings' },
    { href: '/admin/about', label: 'About' },
  ];

  const isActive = (href: string) => {
    if (href === '/admin') {
      return pathname === href;
    }
    if (href === '/admin/contracts') {
      return pathname === href || pathname?.startsWith('/admin/contracts/');
    }
    if (href === '/admin/legal-standards') {
      return pathname === href || pathname?.startsWith('/admin/legal-standards/');
    }
    if (href === '/admin/users') {
      return pathname === href || pathname?.startsWith('/admin/users/');
    }
    if (href === '/admin/theme') {
      return pathname === href || pathname?.startsWith('/admin/theme/');
    }
    return pathname === href;
  };

  return (
    <div className="min-h-screen bg-page flex flex-col">
      {/* Top Navigation */}
      <nav
        className="border-b border-default"
        style={{
          backgroundColor: 'var(--header-bg-color, var(--color-bg-card))',
          height: 'var(--header-height, 64px)'
        }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full">
          <div className="flex items-center justify-between h-full">
            {/* Logo/Brand */}
            <div className="flex items-center gap-8">
              <Link
                href="/admin"
                className="font-bold"
                style={{
                  color: 'var(--header-title-color, var(--color-primary))',
                  fontSize: 'var(--header-font-size, 20px)'
                }}
              >
                Contract Review
              </Link>

              {/* Navigation Links */}
              <div className="hidden md:flex items-center gap-1">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="px-3 py-2 rounded-lg text-sm font-medium transition-colors hover:opacity-80"
                    style={{
                      color: isActive(link.href)
                        ? 'var(--header-nav-active-color, var(--color-primary))'
                        : 'var(--header-nav-color, var(--color-text-muted))'
                    }}
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </div>

            {/* User Menu */}
            <UserMenu />
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4 pb-8 flex-1">
        {children}
      </main>

      {/* Security Footer */}
      <SecurityFooter />
    </div>
  );
}
