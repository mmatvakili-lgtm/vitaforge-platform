"use client";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { ApiError } from "../../../../lib/api/client.ts";
import type { FoodAdmin } from "../../../../lib/api/generated.ts";
import { ALLERGENS } from "../../../../lib/nutrition.ts";
import { blockerKey, canApprove, reviewRequest } from "../../../../lib/review.ts";
import { useApi, useT } from "../../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, Card, Loading } from "../../../../components/ui.tsx";

export default function ReviewPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [rows, setRows] = useState<FoodAdmin[] | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [att, setAtt] = useState<Record<string, { allergensChecked: boolean; allergens: string[]; licenseChecked: boolean }>>({});
  const [bad, setBad] = useState<string | null>(null);
  const [filter, setFilter] = useState<"pending_review" | "all">("pending_review");

  const load = useCallback(async () => {
    const r = await api.call("API-ADM-009");
    if (r.ok) { setRows(r.data); return; }
    if (r.status === 401) return router.replace(`/${locale}/login`);
    if (r.status === 403) { setForbidden(true); return setRows([]); }
    setError(r.error); setRows([]);
  }, [api, router, locale]);
  useEffect(() => { load(); }, [load]);

  async function decide(f: FoodAdmin, decision: "approve" | "reject" | "retire") {
    const body = reviewRequest(decision, notes[f.id] ?? "", att[f.id]);
    if (!body) { setBad(f.id); return; }
    setBad(null); setError(null);
    const r = await api.call("API-ADM-010", { path: { food_id: f.id }, body });
    if (!r.ok) { setError(r.error); await load(); return; }       // a 409 lists the blockers again after reload; nothing was changed
    setNotes({ ...notes, [f.id]: "" }); await load();
  }

  if (rows === null) return <Card title={t("review.title")}><Loading /></Card>;
  if (forbidden) return <Card title={t("review.title")}><Alert kind="warning">{t("review.forbidden")}</Alert></Card>;
  const shown = rows.filter((f) => filter === "all" || f.status === "pending_review");
  return (
    <Card title={t("review.title")}>
      <p>{t("review.intro")}</p>
      <div className="row" role="tablist">
        <Button type="button" role="tab" aria-selected={filter === "pending_review"} onClick={() => setFilter("pending_review")}>{t("review.pending")}</Button>
        <Button type="button" role="tab" aria-selected={filter === "all"} onClick={() => setFilter("all")}>{t("review.all")}</Button>
      </div>
      <ApiErrorView error={error} />
      {shown.length === 0 && <p className="muted">{t("review.empty")}</p>}
      <ul className="plain">
        {shown.map((f) => (
          <li key={f.id} className="card-lite">
            <strong>{f.name_en}</strong> <span className="tag">{t(`review.status.${f.status}`)}</span>
            <p className="muted">{t("review.nutrients", { n: n(f.nutrient_count ?? 0) })} · {f.allergens_known ? t("review.allergensKnown") : t("review.allergensUnknown")}
              {f.source ? ` · ${String(f.source.dataset ?? "")} ${String(f.source.license ?? "")}${f.source.license_verified ? "" : ` (${t("foods.licenseUnverified")})`}` : ` · ${t("foods.noSource")}`}</p>
            {f.approval_blockers.length > 0 && (
              <Alert kind="warning">
                <strong>{t("review.blockers")}</strong>
                <ul>{f.approval_blockers.map((b) => { const k = blockerKey(b); return <li key={b}>{t(k.key)}{k.detail ? `: ${k.detail}` : ""}</li>; })}</ul>
              </Alert>)}
            {f.reviewed_by && <p className="muted">{t("review.lastDecision")}: {f.review_notes}</p>}
            {f.status !== "retired" && (
              <>
                <label htmlFor={`n-${f.id}`}>{t("review.notes")}</label>
                <input id={`n-${f.id}`} value={notes[f.id] ?? ""} maxLength={1000} onChange={(e) => setNotes({ ...notes, [f.id]: e.target.value })} />
                {f.status === "pending_review" && (() => {
                  const a = att[f.id] ?? { allergensChecked: false, allergens: [], licenseChecked: false };
                  const set = (x: Partial<typeof a>) => setAtt({ ...att, [f.id]: { ...a, ...x } });
                  return (
                    <fieldset><legend>{t("review.attest")}</legend>
                      <p className="hint">{t("review.attest.hint")}</p>
                      <label className="check"><input type="checkbox" checked={a.allergensChecked} onChange={(e) => set({ allergensChecked: e.target.checked })} />{t("review.attest.allergens")}</label>
                      {a.allergensChecked && <div className="checks">{ALLERGENS.map((x) => <label key={x} className="check"><input type="checkbox" checked={a.allergens.includes(x)} onChange={(e) => set({ allergens: e.target.checked ? [...a.allergens, x] : a.allergens.filter((y) => y !== x) })} />{t(`allergen.${x}`)}</label>)}</div>}
                      <label className="check"><input type="checkbox" checked={a.licenseChecked} onChange={(e) => set({ licenseChecked: e.target.checked })} />{t("review.attest.license")}</label>
                    </fieldset>);
                })()}
                {bad === f.id && <p className="field-error" role="alert">{t("review.notesRequired")}</p>}
                <div className="row">
                  {f.status === "pending_review" && <Button type="button" disabled={!canApprove(f.approval_blockers)} onClick={() => decide(f, "approve")}>{t("review.approve")}</Button>}
                  {f.status === "pending_review" && <Button type="button" onClick={() => decide(f, "reject")}>{t("review.reject")}</Button>}
                  {f.status === "reviewed" && <Button type="button" onClick={() => decide(f, "retire")}>{t("review.retire")}</Button>}
                </div>
              </>)}
          </li>))}
      </ul>
    </Card>
  );
}
