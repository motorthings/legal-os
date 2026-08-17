'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState, useSyncExternalStore } from 'react';
import { useAuth } from '@/lib/auth';
import { getDescrybeStatus } from '@/lib/legal-research-api';
import {
  FileText, LogOut, Scale, Search, Shield,
  Briefcase, BarChart3, Target, Scale3D,
  Building2, ChevronRight, Gavel, BookOpen,
  LayoutDashboard, FileCheck2,
} from 'lucide-react';

type Persona = 'attorney' | 'leader' | 'tour';

interface NavItem {
  href: string;
  label: string;
  icon: typeof Scale;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const PERSONAS: { id: Persona; label: string; icon: typeof Scale }[] = [
  { id: 'attorney', label: 'Attorney', icon: Briefcase },
  { id: 'leader', label: 'Leader', icon: Building2 },
  { id: 'tour', label: 'Tour', icon: BookOpen },
];

const ALL_FUNCTIONS: NavItem[] = [
  { href: '/matter-intake', label: 'Matter Intake', icon: Search },
  { href: '/contract-review', label: 'Contract Review', icon: FileText },
  { href: '/employment', label: 'Employment', icon: Briefcase },
  { href: '/due-diligence', label: 'Due Diligence', icon: Target },
  { href: '/regulatory', label: 'Regulatory', icon: Shield },
  { href: '/legal-research', label: 'Legal Research', icon: Gavel },
  { href: '/cite-check', label: 'Cite Check', icon: FileCheck2 },
  { href: '/km', label: 'KM Intelligence', icon: BarChart3 },
  { href: '/reporting', label: 'Value Reporting', icon: Scale3D },
  { href: '/simulation', label: 'Firm Simulation', icon: Building2 },
];

const NAV: Record<Persona, NavGroup[]> = {
  attorney: [
    {
      label: 'Practice',
      items: [
        { href: '/employment', label: 'Employment', icon: Briefcase },
        { href: '/due-diligence', label: 'Due Diligence', icon: Target },
        { href: '/regulatory', label: 'Regulatory', icon: Shield },
      ],
    },
    {
      label: 'Tools',
      items: [
        { href: '/contract-review', label: 'Contract Review', icon: FileText },
        { href: '/legal-research', label: 'Legal Research', icon: Gavel },
        { href: '/cite-check', label: 'Cite Check', icon: FileCheck2 },
        { href: '/matter-intake', label: 'Matter Intake', icon: Search },
        { href: '/km', label: 'KM Intelligence', icon: BarChart3 },
      ],
    },
  ],
  leader: [
    {
      label: 'Run it',
      items: [
        { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { href: '/matter-intake', label: 'Matter Pipeline', icon: Search },
        { href: '/km', label: 'KM & Adoption', icon: BarChart3 },
      ],
    },
    {
      label: 'Steer & Prove',
      items: [
        { href: '/reporting', label: 'Value Reporting', icon: Scale3D },
        { href: '/simulation', label: 'Firm Simulation', icon: Building2 },
      ],
    },
  ],
  tour: [
    {
      label: 'Everything',
      items: ALL_FUNCTIONS,
    },
  ],
};

const PERSONA_KEY = 'legal-os-persona';
const PERSONA_EVENT = 'legal-os-persona-change';

function isPersona(value: string | null): value is Persona {
  return value === 'attorney' || value === 'leader' || value === 'tour';
}

// localStorage-backed persona store, read via useSyncExternalStore to avoid
// both hydration mismatch and setState-in-effect.
function getPersonaSnapshot(): Persona {
  if (typeof window === 'undefined') return 'attorney';
  const stored = window.localStorage.getItem(PERSONA_KEY);
  return isPersona(stored) ? stored : 'attorney';
}

function subscribeToPersona(callback: () => void) {
  window.addEventListener('storage', callback);
  window.addEventListener(PERSONA_EVENT, callback);
  return () => {
    window.removeEventListener('storage', callback);
    window.removeEventListener(PERSONA_EVENT, callback);
  };
}

function setPersonaStored(next: Persona) {
  window.localStorage.setItem(PERSONA_KEY, next);
  window.dispatchEvent(new Event(PERSONA_EVENT));
}

export default function Sidebar() {
  const pathname = usePathname();
  const { user, loading, signOut } = useAuth();
  const persona = useSyncExternalStore(
    subscribeToPersona,
    getPersonaSnapshot,
    getPersonaSnapshot
  );
  const [descrybeConnected, setDescrybeConnected] = useState<boolean | null>(null);

  useEffect(() => {
    getDescrybeStatus()
      .then((s) => setDescrybeConnected(s.connected))
      .catch(() => setDescrybeConnected(false));
  }, []);

  const selectPersona = (next: Persona) => setPersonaStored(next);

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + '/');

  const navLinkClass = (active: boolean) =>
    `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline ${
      active
        ? 'text-white'
        : 'text-[var(--text-dim)] hover:bg-[var(--primary-dim)] hover:text-[var(--text)]'
    }`;

  const renderLink = (item: NavItem) => {
    const Icon = item.icon;
    const active = isActive(item.href);
    return (
      <Link
        key={item.href}
        href={item.href}
        className={navLinkClass(active)}
        style={active ? { backgroundColor: 'var(--primary)' } : undefined}
      >
        <Icon className="w-4 h-4" />
        {item.label}
        {item.href === '/legal-research' && (
          <span
            className={`ml-auto w-2 h-2 rounded-full flex-shrink-0 ${
              descrybeConnected === null
                ? 'bg-[var(--text-muted)]/30'
                : descrybeConnected
                ? 'bg-emerald-500'
                : 'bg-amber-500/70'
            }`}
            title={
              descrybeConnected === null
                ? 'Checking Descrybe…'
                : descrybeConnected
                ? 'Descrybe connected'
                : 'Descrybe not connected'
            }
          />
        )}
      </Link>
    );
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

      {/* Persona selector */}
      <div className="p-3 border-b border-[var(--border)]">
        <span className="block px-1 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
          Viewing as
        </span>
        <div className="grid grid-cols-3 gap-1">
          {PERSONAS.map((p) => {
            const Icon = p.icon;
            const active = persona === p.id;
            return (
              <button
                key={p.id}
                onClick={() => selectPersona(p.id)}
                className={`flex flex-col items-center gap-1 px-1 py-2 rounded-lg text-[11px] font-medium transition-colors ${
                  active
                    ? 'text-white'
                    : 'text-[var(--text-dim)] hover:bg-[var(--primary-dim)] hover:text-[var(--text)]'
                }`}
                style={active ? { backgroundColor: 'var(--primary)' } : undefined}
              >
                <Icon className="w-4 h-4" />
                {p.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-3 overflow-y-auto">
        {NAV[persona].map((group) => (
          <div key={group.label}>
            <span className="block px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              {group.label}
            </span>
            <div className="space-y-0.5">{group.items.map(renderLink)}</div>
          </div>
        ))}

        <div className="pt-2 border-t border-[var(--border)]">
          <Link
            href="/guides"
            className={navLinkClass(isActive('/guides'))}
            style={isActive('/guides') ? { backgroundColor: 'var(--primary)' } : undefined}
          >
            <BookOpen className="w-4 h-4" />
            Guides & Diagrams
          </Link>
        </div>
      </nav>

      {/* Descrybe Engine connection status */}
      <div className="px-4 pb-3">
        <div
          className={`flex items-center gap-2.5 px-3 py-2 rounded-lg border ${
            descrybeConnected
              ? 'border-emerald-500/30 bg-emerald-500/5'
              : descrybeConnected === false
              ? 'border-amber-500/30 bg-amber-500/5'
              : 'border-[var(--border)] bg-[var(--surface2)]'
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full flex-shrink-0 ${
              descrybeConnected === null
                ? 'bg-[var(--text-muted)]/40'
                : descrybeConnected
                ? 'bg-emerald-500'
                : 'bg-amber-500'
            }`}
          />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-[var(--text)] leading-tight">Descrybe Engine</p>
            <p
              className={`text-[10px] font-mono leading-tight ${
                descrybeConnected
                  ? 'text-emerald-500'
                  : descrybeConnected === false
                  ? 'text-amber-500'
                  : 'text-[var(--text-muted)]'
              }`}
            >
              {descrybeConnected === null ? 'Checking…' : descrybeConnected ? 'Connected' : 'Not connected'}
            </p>
          </div>
        </div>
      </div>

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
