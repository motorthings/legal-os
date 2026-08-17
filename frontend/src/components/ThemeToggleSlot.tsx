'use client';

import { usePathname } from 'next/navigation';
import ThemeToggle from './ThemeToggle';

// Hides the app-level theme switch on the Guides & Diagrams section. The iframed
// diagrams carry their own (forced-light) theme, so an app toggle there reads as a
// broken control — hide it and let the diagram render in light Gulf Stream Racing.
export default function ThemeToggleSlot() {
  const pathname = usePathname();
  if (pathname.startsWith('/guides')) return null;
  return <ThemeToggle />;
}
