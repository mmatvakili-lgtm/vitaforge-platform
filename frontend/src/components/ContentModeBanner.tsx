"use client";
import { useEffect, useState } from "react";
import { useApi, useT } from "../lib/react/context.tsx";

/** Honest labelling: shown whenever the server runs AI-curated (not expert-reviewed) content, i.e. the public demo. */
export function ContentModeBanner() {
  const { t } = useT();
  const api = useApi();
  const [mode, setMode] = useState<string>("reviewed");
  useEffect(() => {
    void api.call("API-SYS-002").then((r) => { if (r.ok) setMode(r.data.content_mode); });
  }, [api]);
  if (mode === "reviewed") return null;
  return <div className="alert alert-warning" role="note" data-testid="content-mode-banner"><p>{t(mode === "ai_curated_demo" ? "banner.aiCurated" : "banner.devSample")}</p></div>;
}
