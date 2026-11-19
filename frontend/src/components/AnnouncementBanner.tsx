"use client";
import { useEffect, useState } from "react";
import { announcementText, loadAnnouncement, type Announcement } from "../lib/admin.ts";
import { useT } from "../lib/react/context.tsx";

/** Site-wide message set from the admin panel (text only, rendered as plain text). Dismissal lasts for the browser session. */
export function AnnouncementBanner() {
  const { locale, t } = useT();
  const [a, setA] = useState<Announcement | null>(null);
  const [hidden, setHidden] = useState(false);
  useEffect(() => { loadAnnouncement().then(setA); }, []);
  const text = announcementText(a, locale);
  const key = `vf_ann_${text ?? ""}`.slice(0, 120);
  useEffect(() => { try { setHidden(sessionStorage.getItem(key) === "1"); } catch { /* storage unavailable */ } }, [key]);
  if (!text || hidden) return null;
  return (
    <div className={`notice announcement${a?.level === "warning" ? " warn" : ""}`} role="status">
      <span>{text}</span>
      <button type="button" aria-label={t("admin.announce.dismiss")} onClick={() => { setHidden(true); try { sessionStorage.setItem(key, "1"); } catch { /* ignore */ } }}>×</button>
    </div>
  );
}
