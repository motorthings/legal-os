'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import {
  FileText, LogOut, Scale, Search, Shield,
  Briefcase, BarChart3, Target, Scale3D,
  Building2, ChevronRight, Gavel, BookOpen,
  LayoutDashboard, Beaker,
} from 'lucide-react';

interface NavItem {
  href: string;
  label: string;
  icon: typeof Scale;
}

const FUNCTIONS: NavItem[] = [
  { href: '/matter-intake', label: 'Matter Intake', icon: Search },
  { href: '/contract-review', label: 'Contract Review', icon: FileText },
  { href: '/employment', label: 'Employment', icon: Briefcase },
  { href: '/due-diligence', label: 'Due Diligence', icon: Target },
  { href: '/regulatory', label: 'Regulatory', icon: Shield },
  { href: '/km', label: 'KM Intelligence', icon: BarChart3 },
  { href: '/reporting', label: 'Value Reporting', icon: Scale3D },
];

const OPERATIONS: NavItem[] = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/poc-pipeline', label: 'POC Pipeline', icon: Beaker },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, loading, signOut } = useAuth();

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname === href || pathname.startsWith(href + '/');
  };

  return (
    <aside className="w-60 bg-[var(--surface)] border-r border-[var(--border)] flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="p-5 border-b border-[var(--border)]">
        <Link href="/" className="flex items-center gap-3 no-underline">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: 'var(--primary)' }}>
            <Scale className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-[var(--text)]" style={{ fontFamily: "'Fraunces', Georgia, serif" }}>
              Legal AI OS
            </h1>
            <p className="text-[10px] text-[var(--text-muted)] font-mono">
              Governed legal AI
            </p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {/* Home */}
        <Link
          href="/"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline ${
            isActive('/') && pathname === '/'
              ? 'text-white'
              : 'text-[var(--text-dim)] hover:bg-[var(--primary-dim)] hover:text-[var(--text)]'
          }`}
          style={isActive('/') && pathname === '/' ? { backgroundColor: 'var(--primary)' } : undefined}
        >
          <Building2 className="w-4 h-4" />
          Dashboard
        </Link>

        {/* Section header */}
        <div className="pt-4 pb-1 px-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            Platform
          </span>
        </div>

        <Link
          href="/guides"
          className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline ${
            isActive('/guides')
              ? 'text-white'
              : 'text-[var(--text-dim)] hover:bg-[var(--primary-dim)] hover:text-[var(--text)]'
          }`}
          style={isActive('/guides') ? { backgroundColor: 'var(--primary)' } : undefined}
        >
          <BookOpen className="w-4 h-4" />
          Guides & Diagrams
        </Link>

        {/* Section header */}
        <div className="pt-4 pb-1 px-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            Functions
          </span>
        </div>

        {FUNCTIONS.map((fn) => {
          const Icon = fn.icon;
          const active = isActive(fn.href);
          return (
            <Link
              key={fn.href}
              href={fn.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline ${
                active
                  ? 'text-white'
                  : 'text-[var(--text-dim)] hover:bg-[var(--primary-dim)] hover:text-[var(--text)]'
              }`}
              style={active ? { backgroundColor: 'var(--primary)' } : undefined}
            >
              <Icon className="w-4 h-4" />
              {fn.label}
            </Link>
          );
        })}

        {/* Section header */}
        <div className="pt-4 pb-1 px-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            Operations
          </span>
        </div>

        {OPERATIONS.map((op) => {
          const Icon = op.icon;
          const active = isActive(op.href);
          return (
            <Link
              key={op.href}
              href={op.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline ${
                active
                  ? 'text-white'
                  : 'text-[var(--text-dim)] hover:bg-[var(--primary-dim)] hover:text-[var(--text)]'
              }`}
              style={active ? { backgroundColor: 'var(--primary)' } : undefined}
            >
              <Icon className="w-4 h-4" />
              {op.label}
            </Link>
          );
        })}
      </nav>

      {/* User section */}
      <div className="p-4 border-t border-[var(--border)]">
        {loading ? (
          <div className="h-10 rounded-lg bg-[var(--surface2)] animate-pulse" />
        ) : user ? (
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium text-[var(--text)] truncate">
                {user.user_metadata?.display_name || user.email?.split('@')[0] || 'User'}
              </p>
              <p className="text-xs text-[var(--text-muted)] truncate">{user.email}</p>
            </div>
            <button
              onClick={signOut}
              className="p-1.5 text-[var(--text-muted)] hover:text-[var(--rose)] transition-colors rounded-lg hover:bg-[var(--primary-dim)]"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-[var(--text-dim)] hover:bg-[var(--primary-dim)] hover:text-[var(--text)] transition-colors no-underline"
          >
            <ChevronRight className="w-4 h-4" />
            Sign In
          </Link>
        )}
      </div>
    </aside>
  );
}
