"use client";
import { useEffect, useState } from "react";
import { useT } from "../lib/react/context.tsx";

const THEMES = ["system", "forge", "lab", "track"] as const;
type Theme = (typeof THEMES)[number];

export function ThemeSwitcher() {
  const { t } = useT();
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => {
    try { const v = localStorage.getItem("vf_theme"); if (v === "forge" || v === "lab" || v === "track") setTheme(v); } catch { /* storage may be blocked */ }
  }, []);
  function choose(v: Theme) {
    setTheme(v);
    if (v === "system") document.documentElement.removeAttribute("data-theme"); else document.documentElement.setAttribute("data-theme", v);
    try { if (v === "system") localStorage.removeItem("vf_theme"); else localStorage.setItem("vf_theme", v); } catch { /* ignore */ }
  }
  return (
    <select className="theme-switch" aria-label={t("nav.theme")} value={theme} onChange={(e) => choose(e.target.value as Theme)}>
      {THEMES.map((v) => <option key={v} value={v}>{t(`theme.${v}`)}</option>)}
    </select>
  );
}
