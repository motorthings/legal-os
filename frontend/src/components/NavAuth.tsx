"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function NavAuth() {
  const { user, loading, signOut } = useAuth();

  if (loading) return null;

  if (!user) {
    return (
      <Link
        href="/login"
        className="font-mono text-xs text-[var(--text-dim)] hover:text-[var(--secondary)] no-underline transition-colors"
      >
        Sign In
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-[var(--text-dim)] font-mono hidden sm:inline">
        {user.email}
      </span>
      <button
        onClick={signOut}
        className="font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)] hover:text-[var(--rose)] bg-transparent border-0 cursor-pointer transition-colors"
      >
        Sign Out
      </button>
    </div>
  );
}
