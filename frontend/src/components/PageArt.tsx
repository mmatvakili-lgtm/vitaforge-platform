"use client";
import { usePathname } from "next/navigation";

/** Small animated emblem per section (draws itself on arrival). Decorative only. */
export function PageArt() {
  const seg = (usePathname() ?? "").split("/")[2] ?? "";
  const art = ART[seg];
  if (!art) return null;
  return <svg className="pa" viewBox="0 0 120 80" aria-hidden="true" focusable="false" key={seg}>{art}</svg>;
}

const ART: Record<string, React.ReactNode> = {
  plan: <><rect x="10" y="14" width="100" height="58" rx="8" pathLength={1} className="dr" /><path d="M10 32h100M34 6v14M86 6v14" pathLength={1} className="dr" /><circle cx="36" cy="52" r="5" className="fill blink" /><path d="M54 52h40" pathLength={1} className="dr" /></>,
  nutrition: <><circle cx="60" cy="42" r="30" className="ring" /><circle cx="60" cy="42" r="19" className="ring" /><path d="M60 12v30l22 14" className="pulse dr" pathLength={1} /></>,
  analytics: <><path d="M14 70V40" className="up" /><path d="M36 70V28" className="up" /><path d="M58 70V46" className="up" /><path d="M80 70V18" className="up" /><path d="M102 70V34" className="up" /><path d="M10 50 36 34 58 48 80 20 108 30" className="pulse dr" pathLength={1} /></>,
  health: <path d="M6 44h24l10-26 16 52 12-34 8 8h38" className="pulse dr" pathLength={1} />,
  body: <><circle cx="60" cy="14" r="9" className="ring" /><path d="M42 34h36l6 26M42 34l-6 26M50 34v38M70 34v38" pathLength={1} className="dr" /></>,
  history: <><circle cx="60" cy="42" r="30" className="ring" /><path d="M60 22v20l14 8" className="pulse dr" pathLength={1} /><path d="M14 20l-6 12 12 2" pathLength={1} className="dr" /></>,
  exercises: <><path d="M8 42h104M22 24v36M34 18v48M86 18v48M98 24v36" pathLength={1} className="dr" /></>,
  assessment: <><path d="M20 70V30l40-18 40 18v40z" pathLength={1} className="dr" /><path d="M44 46l12 12 22-24" className="pulse dr" pathLength={1} /></>,
  foods: <><circle cx="60" cy="44" r="28" className="ring" /><path d="M60 16c0-8 8-10 14-10" pathLength={1} className="dr" /></>,
  profile: <><circle cx="60" cy="26" r="14" className="ring" /><path d="M24 74c4-22 20-28 36-28s32 6 36 28" pathLength={1} className="dr" /></>,
};
