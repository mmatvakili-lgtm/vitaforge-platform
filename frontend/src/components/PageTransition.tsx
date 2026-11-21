"use client";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

/** Re-keys the page content on every route change so each page plays its entrance (staggered by CSS); the shell around it never remounts. */
export function PageTransition({ children }: { children: ReactNode }) {
  const path = usePathname();
  return <div key={path} className="route-in">{children}</div>;
}
