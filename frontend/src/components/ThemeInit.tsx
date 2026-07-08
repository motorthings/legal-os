"use client";

import { useEffect } from "react";

export default function ThemeInit() {
  useEffect(() => {
    const btn = document.getElementById("themeToggleBtn");
    if (!btn) return;
    const lightIcon = btn.querySelector(".light-icon") as HTMLElement | null;
    const darkIcon = btn.querySelector(".dark-icon") as HTMLElement | null;

    function update() {
      const isDark = document.documentElement.classList.contains("dark");
      if (lightIcon) lightIcon.style.display = isDark ? "none" : "";
      if (darkIcon) darkIcon.style.display = isDark ? "" : "none";
    }

    update();
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, []);

  return null;
}
