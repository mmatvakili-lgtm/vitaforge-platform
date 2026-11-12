"use client";
import { useEffect, useState } from "react";
import type { ProgressionItem } from "../lib/api/generated.ts";
import { progressionTone } from "../lib/nutrition-log.ts";
import { useApi, useT } from "../lib/react/context.tsx";
import { Alert } from "./ui.tsx";

/** Suggestions only: the user decides; the Safety Core still gates what the plan may contain. */
export function Progression({ names }: { names: Record<string, string> }) {
  const { t, n } = useT();
  const api = useApi();
  const [items, setItems] = useState<ProgressionItem[] | null>(null);
  useEffect(() => {
    let live = true;
    api.call("API-WO-005").then((r) => { if (live) setItems(r.ok ? r.data.items : []); });
    return () => { live = false; };
  }, [api]);
  const rows = (items ?? []).filter((i) => i.exercise_id in names);
  if (rows.length === 0) return null;
  return (
    <section aria-label={t("prog.title")}>
      <h2>{t("prog.title")}</h2>
      <p className="hint">{t("prog.hint")}</p>
      <ul className="plain">
        {rows.map((i) => (
          <li key={i.exercise_id}>
            <strong>{names[i.exercise_id]}</strong>: {t(`prog.action.${i.action}`)}
            {i.new_load_kg !== undefined && <> — {t("prog.load", { kg: n(i.new_load_kg) })}</>}
            {i.target_reps !== undefined && <> × {t("prog.reps", { n: n(i.target_reps) })}</>}
            {progressionTone(i.action) === "stop" && <Alert kind="warning">{t(`prog.action.${i.action}`)}</Alert>}
            <span className="muted"> ({t(`plan.confidence.${i.confidence}`)})</span>
            <ul className="plain">{i.reasons.map((r) => <li key={r} className="muted">{t(`prog.reason.${r}`) === `prog.reason.${r}` ? r : t(`prog.reason.${r}`)}</li>)}</ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
