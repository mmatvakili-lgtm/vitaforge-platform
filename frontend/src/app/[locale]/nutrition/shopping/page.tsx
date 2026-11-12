"use client";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import type { ApiError } from "../../../../lib/api/client.ts";
import type { MealPlanRequest, MealPlanResponse, UserPrice } from "../../../../lib/api/generated.ts";
import { budgetState, mealView, validateMealRequest } from "../../../../lib/nutrition.ts";
import { pruneChecked, toggleChecked, validatePrice } from "../../../../lib/nutrition-log.ts";
import { normalizeDigits } from "../../../../lib/i18n.ts";
import { useApi, useT } from "../../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, ButtonLink, Card, Field, Loading } from "../../../../components/ui.tsx";

export default function ShoppingPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [plan, setPlan] = useState<MealPlanResponse | null>(null);
  const [wantedBudget, setWantedBudget] = useState(false);
  const [checked, setChecked] = useState<string[]>([]);
  const [prices, setPrices] = useState<UserPrice[]>([]);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [days, setDays] = useState("7"); const [budget, setBudget] = useState(""); const [currency, setCurrency] = useState(""); const [region, setRegion] = useState("");
  const [priceDraft, setPriceDraft] = useState<Record<string, string>>({});
  const [priceErr, setPriceErr] = useState<string | null>(null);
  const [fe, setFe] = useState<Record<string, string>>({});

  const fail = useCallback((e: ApiError, s: number) => {
    if (s === 401) { router.replace(`/${locale}/login`); return; }
    if (e.code === "consent_required") { setConsent(true); return; }
    setError(e);
  }, [router, locale]);

  useEffect(() => {
    let live = true;
    Promise.all([api.call("API-NUT-012"), api.call("API-NUT-009")]).then(([a, b]) => {
      if (!live) return;
      if (a.ok) setChecked(a.data.checked); else if (a.status === 401) return router.replace(`/${locale}/login`);
      if (b.ok) setPrices(b.data.prices);
      setReady(true);
    });
    return () => { live = false; };
  }, [api, router, locale]);

  const generate = useCallback(async (d: string, b: string, c: string, r: string) => {
    const body: MealPlanRequest = { days: Number(normalizeDigits(d)) || 7, ...(b.trim() ? { weekly_budget: Number(normalizeDigits(b)), currency: c.trim(), region: r.trim() } : {}) };
    setBusy(true); setError(null); setWantedBudget(!!b.trim());
    const res = await api.call("API-NUT-003", { body });
    setBusy(false);
    if (!res.ok) return fail(res.error, res.status);
    setPlan(res.data);
  }, [api, fail]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errs = validateMealRequest({ budget, currency, region });
    setFe(errs); if (Object.keys(errs).length) return;
    await generate(days, budget, currency, region);
  }

  async function tick(id: string) {
    const next = toggleChecked(checked, id);
    setChecked(next);                                                    // optimistic; reverted if the server rejects it
    const r = await api.call("API-NUT-013", { body: { checked: next } });
    if (!r.ok) { setChecked(checked); fail(r.error, r.status); }
  }

  async function savePrice(foodId: string) {
    const body = validatePrice({ food_id: foodId, price: priceDraft[foodId] ?? "", currency: currency || prices[0]?.currency || "", region: region || prices[0]?.region || "" });
    if (!body) { setPriceErr(foodId); return; }
    setPriceErr(null);
    const r = await api.call("API-NUT-010", { body });
    if (!r.ok) return fail(r.error, r.status);
    setPrices([...prices.filter((p) => p.food_id !== foodId), r.data]); setPriceDraft({ ...priceDraft, [foodId]: "" });
    await generate(days, budget, currency || body.currency, region || body.region);
  }
  async function dropPrice(foodId: string) {
    const r = await api.call("API-NUT-011", { path: { food_id: foodId } });
    if (!r.ok) return fail(r.error, r.status);
    setPrices(prices.filter((p) => p.food_id !== foodId));
  }

  if (!ready) return <Card title={t("nut.shop.title")}><Loading /></Card>;
  if (consent) return <Card title={t("nut.shop.title")}><Alert kind="warning">{t("nut.consent.needed")}</Alert><ButtonLink href={`/${locale}/onboarding?stage=consent`}>{t("nut.consent.action")}</ButtonLink></Card>;

  const view = plan ? mealView(plan) : null;
  const shopping = view?.kind === "plan" ? view.res.shopping : [];
  const ids = shopping.map((s) => s.food_id ?? "");
  const live = pruneChecked(checked, ids);
  const priceOf = (id: string) => prices.find((p) => p.food_id === id);

  return (
    <>
      <Card title={t("nut.shop.title")}>
        <ApiErrorView error={error} />
        <form onSubmit={submit} noValidate>
          <Field id="sd" label={t("nut.days")}><select id="sd" value={days} onChange={(e) => setDays(e.target.value)}>{[1, 2, 3, 4, 5, 6, 7].map((d) => <option key={d} value={d}>{d}</option>)}</select></Field>
          <p className="hint">{t("nut.budget.hint")}</p>
          <div className="row">
            <Field id="sb" label={t("nut.budget")} error={fe.weekly_budget ? t("error.validation_failed") : undefined}><input id="sb" inputMode="decimal" dir="ltr" value={budget} onChange={(e) => setBudget(e.target.value)} /></Field>
            <Field id="sc" label={t("nut.currency")} error={fe.currency ? t("error.validation_failed") : undefined}><input id="sc" dir="ltr" maxLength={3} value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} /></Field>
            <Field id="sr" label={t("nut.region")} error={fe.region ? t("error.validation_failed") : undefined}><input id="sr" dir="ltr" value={region} onChange={(e) => setRegion(e.target.value)} /></Field>
          </div>
          <Button type="submit" busy={busy}>{plan ? t("nut.regenerate") : t("nut.generate")}</Button>
        </form>
      </Card>

      {view && view.kind !== "plan" && <Card><Alert kind="info"><strong>{t("nut.content.title")}</strong> {t(view.kind === "needs_content" ? "nut.content.body" : "nut.needsinfo.body")}</Alert></Card>}

      {view?.kind === "plan" && (
        <Card title={t("nut.shop.title")}>
          {shopping.length === 0 ? <p className="muted">{t("nut.shop.empty")}</p> : (
            <ul className="plain">
              {shopping.map((s) => {
                const id = s.food_id ?? ""; const q = priceOf(id);
                return (
                  <li key={id}>
                    <label className="check"><input type="checkbox" checked={live.includes(id)} onChange={() => tick(id)} /> {s.name_en} — {n(Math.round(s.grams ?? 0))} g{s.in_pantry ? ` (${t("nut.shop.pantry")})` : ""}</label>
                    {" "}<span className="muted">{s.cost != null ? `${t("nut.shop.cost")}: ${n(Math.round(s.cost))}` : t("nut.shop.noPrice")}</span>
                    <div className="row">
                      <input aria-label={t("shop.pricePerKg")} inputMode="decimal" dir="ltr" placeholder={q ? `${q.price_per_kg} ${q.currency}` : t("shop.pricePerKg")} value={priceDraft[id] ?? ""} onChange={(e) => setPriceDraft({ ...priceDraft, [id]: e.target.value })} />
                      <Button type="button" onClick={() => savePrice(id)}>{t("shop.savePrice")}</Button>
                      {q && <button type="button" className="linklike" onClick={() => dropPrice(id)}>{t("shop.removePrice")}</button>}
                    </div>
                    {priceErr === id && <p className="field-error" role="alert">{t("shop.priceInvalid")}</p>}
                    {q && <p className="muted">{t("shop.userEntered", { date: q.observed_on })}</p>}
                  </li>);
              })}
            </ul>
          )}
          <p>{(() => { const b = budgetState(view.res, wantedBudget); return t(`nut.budget.${b}`); })()}</p>
          {view.res.total_cost != null && <p>{t("nut.budget.total", { n: Math.round(view.res.total_cost) })}</p>}
          {(view.res.unpriced_food_ids ?? []).length > 0 && <p className="muted">{t("nut.budget.unpriced", { n: view.res.unpriced_food_ids!.length })}</p>}
          <p className="muted">{view.res.labels.map((l) => t(`nut.label.${l}`)).join(" · ")}</p>
        </Card>
      )}
    </>
  );
}
