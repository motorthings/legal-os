"use client";

import { useState, useEffect } from "react";
import { Sun, Moon } from "lucide-react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(true);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  const toggle = () => {
    const html = document.documentElement;
    html.classList.toggle("dark");
    const next = html.classList.contains("dark");
    setDark(next);
    localStorage.setItem("legal-os-theme", next ? "dark" : "light");
  };

  return (
    <button
      onClick={toggle}
      className="w-9 h-9 rounded-lg border border-[var(--border)] bg-[var(--surface)] cursor-pointer flex items-center justify-center text-[var(--text-dim)] hover:border-[var(--primary)] hover:text-[var(--primary)] transition-all"
      aria-label="Toggle dark mode"
    >
      {dark ? (
        <Moon className="w-4 h-4" />
      ) : (
        <Sun className="w-4 h-4" />
      )}
    </button>
  );
}
