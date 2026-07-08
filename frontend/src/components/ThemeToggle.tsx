"use client";

export default function ThemeToggle() {
  return (
    <button
      id="themeToggleBtn"
      className="w-9 h-9 rounded-lg border border-[var(--border)] bg-[var(--surface)] cursor-pointer flex items-center justify-center text-lg text-[var(--text-dim)] hover:border-[var(--primary)] hover:text-[var(--primary)] transition-all"
      aria-label="Toggle dark mode"
      onClick={() => {
        const html = document.documentElement;
        html.classList.toggle("dark");
        localStorage.setItem(
          "legal-os-theme",
          html.classList.contains("dark") ? "dark" : "light"
        );
      }}
    >
      <span className="light-icon">&#9788;</span>
      <span className="dark-icon hidden">&#9790;</span>
    </button>
  );
}
