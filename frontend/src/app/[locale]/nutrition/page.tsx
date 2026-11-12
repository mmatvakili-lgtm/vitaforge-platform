"use client";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { MealPlanMeal, MealPlanRequest, MealPlanResponse, NutritionEstimate } from "../../../lib/api/generated.ts";
import { normalizeDigits } from "../../../lib/i18n.ts";
import {
  ACTIVITY, ALLERGENS, DIET_TAGS, SCREEN_KEYS, SLOTS, budgetState, buildProfileRequest, dayLabel, macroRanges, mealView, nutrientLines, reasonText,
  validateMealRequest, validateProfile, type FieldErrors,
} from "../../../lib/nutrition.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, ButtonLink, Card, Field, Loading } from "../../../components/ui.tsx";

const num = (s: string) => (s.trim() === "" ? undefined : Number(normalizeDigits(s.trim())));

function Labels({ labels }: { labels: string[] }) {
  const { t } = useT();
  return (
    <p className="chips">{labels.map((l) => <span key={l} className="tag">{t(`nut.label.${l}`) === `nut.label.${l}` ? l : t(`nut.label.${l}`)}</span>)}</p>
  );
}

function EstimateCard({ e }: { e: NutritionEstimate }) {
  const { t, n } = useT();
  const tdee = e.tdee && e.tdee.length === 3 ? e.tdee : undefined;
  const macros = macroRanges(e);
  return (
    <Card title={t("nut.estimate.title")}>
      <Labels labels={e.labels ?? []} />
      {tdee && <p><strong>{t("nut.estimate.tdee")}:</strong> {t("nut.estimate.range", { low: n(tdee[0]), high: n(tdee[2]) })} <span className="muted">({n(tdee[1])})</span></p>}
      {Object.keys(macros).length > 0 && (<><h2>{t("nut.estimate.macros")}</h2><ul className="plain">{Object.entries(macros).map(([k, [a, b]]) => (
        <li key={k}>{t(`nutrient.${k}`)}: {n(a)}–{n(b)}</li>))}</ul></>)}
      {e.water_ml && <p>{t("nut.estimate.water")}: {n(e.water_ml[0])}–{n(e.water_ml[1])}</p>}
      {e.uncertainty && <p className="muted">{t("nut.estimate.uncertainty", { u: t(`nut.unc.${e.uncertainty}`) })}</p>}
      {e.goal_adjustment && e.goal_adjustment !== "enabled" && <p className="muted">{t("nut.estimate.goalNote")}</p>}
    </Card>
  );
}

function MealCard({ m }: { m: MealPlanMeal }) {
  const { locale, t, n } = useT();
  const [open, setOpen] = useState(false);
  const lines = nutrientLines(m.nutrients);
  const name = (locale === "fa" ? m.name_fa : null) ?? m.name_en;
  return (
    <article className="meal">
      <h3>{t(`nut.slot.${m.slot}`)} — {name}</h3>
      <p className="muted">{t("nut.meal.portion", { n: m.portion ?? 1 })} · {t("nut.meal.cook", { n: m.cook_minutes ?? 0 })}{m.cost != null && ` · ${t("nut.shop.cost", { n: m.cost })}`}</p>
      {lines.length > 0 && <p className="macros">{lines.slice(0, 4).map((l) => `${t(`nutrient.${l.key}`)} ${n(Math.round(l.value))} ${t(`nutrient.${l.key}.unit`)}`).join(" · ")}</p>}
      <p className="allergens">{(m.allergens ?? []).length > 0 ? t("nut.meal.allergens", { list: m.allergens!.map((a) => t(`allergen.${a}`)).join("، ") }) : t("nut.meal.noAllergens")}
        {m.allergens_known === false && <strong> — {t("nut.meal.allergensUnknown")}</strong>}</p>
      <button type="button" className="btn-secondary" aria-expanded={open} onClick={() => setOpen(!open)}>{t("nut.meal.show")}</button>
      {open && (
        <div>
          <h4>{t("nut.meal.ingredients")}</h4>
          <ul>{(m.ingredients ?? []).map((i) => <li key={i.food_id}>{(locale === "fa" ? i.name_fa : null) ?? i.name_en} — {t("nut.shop.grams", { n: i.grams ?? 0 })}</li>)}</ul>
          <h4>{t("nut.meal.steps")}</h4>
          {(m.steps ?? []).length > 0 ? <ol>{m.steps!.map((s, k) => <li key={k}>{s}</li>)}</ol> : <p className="muted">{t("nut.meal.noSteps")}</p>}
          {(m.missing_nutrients ?? []).length > 0 && <p className="muted">{t("nut.meal.missing")}</p>}
        </div>
      )}
    </article>
  );
}

function PlanView({ res, wantedBudget }: { res: MealPlanResponse; wantedBudget: boolean }) {
  const { locale, t, n } = useT();
  const [tab, setTab] = useState<number | "shop">(0);
  const bs = budgetState(res, wantedBudget);
  const day = typeof tab === "number" ? res.days[tab] : undefined;
  return (
    <div>
      <Labels labels={res.labels} />
      {(res.labels.includes("unreviewed_food_data") || res.labels.includes("test_fixture_data")) && <Alert kind="warning"><strong>{t("nut.unreviewed.title")}</strong><p>{t("nut.unreviewed.body")}</p></Alert>}
      <Alert kind={bs === "met" ? "success" : bs === "none" ? "info" : "warning"}>
        <p>{t(`nut.budget.${bs}`)}</p>
        {bs !== "none" && res.total_cost != null && <p>{t("nut.budget.total", { n: res.total_cost })}</p>}
        {bs === "unverifiable" && (res.unpriced_food_ids ?? []).length > 0 && <p>{t("nut.budget.unpriced", { n: res.unpriced_food_ids!.length })}</p>}
      </Alert>
      <ul className="plain notes">{res.reasons.filter((r) => r !== "NUT-PLAN-ESTIMATE" || true).map((r) => <li key={r} className="muted">{reasonText(locale, r)}</li>)}</ul>
      <div role="tablist" aria-label={t("nut.view.week")} className="tabs">
        {res.days.map((d, i) => {
          const l = dayLabel(d.date ?? "1970-01-01", locale);
          return (<button key={d.index ?? i} role="tab" aria-selected={tab === i} className={tab === i ? "tab active" : "tab"} onClick={() => setTab(i)}><span>{l.weekday}</span><small>{l.day}</small></button>);
        })}
        <button role="tab" aria-selected={tab === "shop"} className={tab === "shop" ? "tab active" : "tab"} onClick={() => setTab("shop")}>{t("nut.view.shopping")}</button>
      </div>
      {day && (
        <section role="tabpanel">
          {SLOTS.flatMap((s) => (day.meals ?? []).filter((m) => m.slot === s)).map((m, i) => <MealCard key={`${m.slot}-${m.recipe_id}-${i}`} m={m} />)}
          <p><strong>{t("nut.day.total")}:</strong> {n(day.kcal ?? 0)} {t("nutrient.kcal.unit")} · {t("nutrient.protein_g")} {n(day.protein_g ?? 0)} {t("nutrient.protein_g.unit")}</p>
          {res.target_kcal != null && <p className="muted">{t("nut.day.target", { n: Math.round(res.target_kcal) })}</p>}
        </section>
      )}
      {tab === "shop" && (
        <section role="tabpanel">
          <h2>{t("nut.shop.title")}</h2>
          {res.shopping.length === 0 ? <p className="muted">{t("nut.shop.empty")}</p> : (
            <ul className="shopping">{res.shopping.map((s) => (
              <li key={s.food_id}><strong>{s.name_en}</strong> — {t("nut.shop.grams", { n: s.grams ?? 0 })}
                {s.in_pantry ? <span className="tag">{t("nut.shop.pantry")}</span> : <span className="muted"> · {s.cost != null ? t("nut.shop.cost", { n: s.cost }) : t("nut.shop.noPrice")}</span>}</li>))}</ul>
          )}
        </section>
      )}
    </div>
  );
}

export default function NutritionPage() {
  const { locale, t } = useT();
  const api = useApi();
  const router = useRouter();
  const [boot, setBoot] = useState<"loading" | "ready">("loading");
  const [estimate, setEstimate] = useState<NutritionEstimate | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [consentNeeded, setConsentNeeded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [fe, setFe] = useState<FieldErrors>({});

  const [height, setHeight] = useState(""); const [weight, setWeight] = useState(""); const [activity, setActivity] = useState(""); const [sex, setSex] = useState("");
  const [screen, setScreen] = useState<Record<string, boolean | undefined>>({});
  const [editing, setEditing] = useState(false); const [pAllergens, setPAllergens] = useState<string[]>([]); const [pDiet, setPDiet] = useState<string[]>([]);

  const [days, setDays] = useState("7"); const [allergens, setAllergens] = useState<string[]>([]); const [diet, setDiet] = useState<string[]>([]);
  const [maxCook, setMaxCook] = useState(""); const [budget, setBudget] = useState(""); const [currency, setCurrency] = useState(""); const [region, setRegion] = useState("");
  const [plan, setPlan] = useState<MealPlanResponse | null>(null);
  const [wantedBudget, setWantedBudget] = useState(false);

  const fail = useCallback((e: ApiError, status: number) => {
    if (status === 401) { router.replace(`/${locale}/login`); return; }
    if (e.code === "consent_required") { setConsentNeeded(true); return; }
    setError(e);
  }, [router, locale]);

  useEffect(() => {
    let live = true;
    api.call("API-NUT-002").then((r) => {
      if (!live) return;
      if (r.ok) { setEstimate(r.data); setPAllergens(r.data.allergens ?? []); setPDiet(r.data.diet_required ?? []); setAllergens(r.data.allergens ?? []); setDiet(r.data.diet_required ?? []); } else if (r.status !== 404) fail(r.error, r.status);
      setBoot("ready");
    });
    return () => { live = false; };
  }, [api, fail]);

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    const p = { height_cm: num(height), weight_kg: num(weight), activity, screening: screen };
    const errs = validateProfile(p);
    setFe(errs);
    if (Object.keys(errs).length) return;
    setBusy(true); setError(null);
    const r = await api.call("API-NUT-001", { body: buildProfileRequest({ sex, height_cm: p.height_cm!, weight_kg: p.weight_kg!, activity, screening: screen as Record<string, boolean>, allergens: pAllergens, diet_required: pDiet }) });
    setBusy(false);
    if (!r.ok) return fail(r.error, r.status);
    setEstimate(r.data); setPlan(null); setEditing(false);
    setAllergens(r.data.allergens ?? []); setDiet(r.data.diet_required ?? []);
  }

  async function generate(e: FormEvent) {
    e.preventDefault();
    const errs = validateMealRequest({ budget, currency, region, maxCook });
    setFe(errs);
    if (Object.keys(errs).length) return;
    const body: MealPlanRequest = { days: Number(normalizeDigits(days)) || 7, allergens: allergens as MealPlanRequest["allergens"], diet_required: diet as MealPlanRequest["diet_required"],
      ...(maxCook.trim() ? { max_cook_minutes: Number(normalizeDigits(maxCook)) } : {}),
      ...(budget.trim() ? { weekly_budget: Number(normalizeDigits(budget)), currency: currency.trim(), region: region.trim() } : {}) };
    setBusy(true); setError(null); setWantedBudget(!!budget.trim());
    const r = await api.call("API-NUT-003", { body });
    setBusy(false);
    if (!r.ok) return fail(r.error, r.status);
    setPlan(r.data);
  }

  const view = useMemo(() => (plan ? mealView(plan) : null), [plan]);
  const eligible = estimate?.status === "OK";

  if (boot === "loading") return <Card title={t("nut.title")}><Loading /></Card>;
  if (consentNeeded) return (
    <Card title={t("nut.title")}><Alert kind="warning">{t("nut.consent.needed")}</Alert><ButtonLink href={`/${locale}/onboarding?stage=consent`}>{t("nut.consent.action")}</ButtonLink></Card>
  );

  const tog = (list: string[], set: (v: string[]) => void, v: string, on: boolean) => set(on ? [...list, v] : list.filter((x) => x !== v));
  return (
    <>
      <Card title={t("nut.title")}><p>{t("nut.intro")}</p><ApiErrorView error={error} /></Card>

      {(!estimate || editing) && (
        <Card title={t("nut.profile.title")}>
          <form onSubmit={saveProfile} noValidate>
            <Field id="height" label={t("nut.height")} error={fe.height_cm ? t("error.validation_failed") : undefined}><input id="height" inputMode="decimal" dir="ltr" value={height} onChange={(e) => setHeight(e.target.value)} /></Field>
            <Field id="weight" label={t("nut.weight")} error={fe.weight_kg ? t("error.validation_failed") : undefined}><input id="weight" inputMode="decimal" dir="ltr" value={weight} onChange={(e) => setWeight(e.target.value)} /></Field>
            <Field id="activity" label={t("nut.activity")} error={fe.activity ? t("error.validation_failed") : undefined}>
              <select id="activity" value={activity} onChange={(e) => setActivity(e.target.value)}><option value="" />{ACTIVITY.map((a) => <option key={a} value={a}>{t(`activity.${a}`)}</option>)}</select>
            </Field>
            <Field id="sex" label={t("nut.sex")}>
              <select id="sex" value={sex} onChange={(e) => setSex(e.target.value)}><option value="">{t("sex.unset")}</option><option value="male">{t("sex.male")}</option><option value="female">{t("sex.female")}</option></select>
            </Field>
            <h2>{t("nut.screen.title")}</h2>
            {SCREEN_KEYS.map((k) => (
              <fieldset key={k} className="yn"><legend>{t(`nut.screen.${k}`)}</legend>
                <label className="check"><input type="radio" name={k} checked={screen[k] === true} onChange={() => setScreen({ ...screen, [k]: true })} />{t("screening.yes")}</label>
                <label className="check"><input type="radio" name={k} checked={screen[k] === false} onChange={() => setScreen({ ...screen, [k]: false })} />{t("screening.no")}</label>
              </fieldset>))}
            {fe.screening && <p className="field-error" role="alert">{t("screening.unanswered")}</p>}
            <fieldset><legend>{t("nut.allergens")}</legend><p className="hint">{t("nut.profile.allergens.hint")}</p>
              <div className="checks">{ALLERGENS.map((a) => <label key={a} className="check"><input type="checkbox" checked={pAllergens.includes(a)} onChange={(e) => tog(pAllergens, setPAllergens, a, e.target.checked)} />{t(`allergen.${a}`)}</label>)}</div></fieldset>
            <fieldset><legend>{t("nut.diet")}</legend>
              <div className="checks">{DIET_TAGS.map((d) => <label key={d} className="check"><input type="checkbox" checked={pDiet.includes(d)} onChange={(e) => tog(pDiet, setPDiet, d, e.target.checked)} />{t(`diet.${d}`)}</label>)}</div></fieldset>
            <Button type="submit" busy={busy}>{t("nut.profile.save")}</Button>
          </form>
        </Card>
      )}

      {estimate && !editing && <div className="row"><Button type="button" onClick={() => setEditing(true)}>{t("nut.profile.edit")}</Button>
        <ButtonLink href={`/${locale}/nutrition/log`} secondary>{t("nut.log.title")}</ButtonLink>
        <ButtonLink href={`/${locale}/nutrition/shopping`} secondary>{t("nut.shop.title")}</ButtonLink>
        <ButtonLink href={`/${locale}/foods`} secondary>{t("foods.title")}</ButtonLink></div>}
      {estimate && estimate.status === "OK" && <EstimateCard e={estimate} />}
      {estimate && estimate.status !== "OK" && (
        <Card title={t("nut.refer.title")}>
          <Alert kind="error"><p>{estimate.status === "REFER" ? t("nut.refer.body") : estimate.status === "BLOCKED" ? t("nut.blocked.body") : t("nut.needsinfo.body")}</p></Alert>
          <ul className="plain">{(estimate.reasons ?? []).map((r) => <li key={r} className="muted">{reasonText(locale, r)}</li>)}</ul>
          {estimate.status === "BLOCKED" && <ButtonLink href={`/${locale}/onboarding`}>{t("nav.onboarding")}</ButtonLink>}
        </Card>
      )}

      {eligible && (
        <Card title={t("nut.prefs.title")}>
          <form onSubmit={generate} noValidate>
            <Field id="days" label={t("nut.days")}><select id="days" value={days} onChange={(e) => setDays(e.target.value)}>{[1, 2, 3, 4, 5, 6, 7].map((d) => <option key={d} value={d}>{d}</option>)}</select></Field>
            <fieldset><legend>{t("nut.allergens")}</legend><p className="hint">{t("nut.allergens.hint")}</p>
              <div className="checks">{ALLERGENS.map((a) => <label key={a} className="check"><input type="checkbox" checked={allergens.includes(a)} onChange={(e) => tog(allergens, setAllergens, a, e.target.checked)} />{t(`allergen.${a}`)}</label>)}</div></fieldset>
            <fieldset><legend>{t("nut.diet")}</legend>
              <div className="checks">{DIET_TAGS.map((d) => <label key={d} className="check"><input type="checkbox" checked={diet.includes(d)} onChange={(e) => tog(diet, setDiet, d, e.target.checked)} />{t(`diet.${d}`)}</label>)}</div></fieldset>
            <Field id="cook" label={t("nut.maxCook")} error={fe.max_cook_minutes ? t("error.validation_failed") : undefined}><input id="cook" inputMode="numeric" dir="ltr" value={maxCook} onChange={(e) => setMaxCook(e.target.value)} /></Field>
            <Field id="budget" label={t("nut.budget")} hint={t("nut.budget.hint")} error={fe.weekly_budget ? t("error.validation_failed") : undefined}><input id="budget" inputMode="decimal" dir="ltr" value={budget} onChange={(e) => setBudget(e.target.value)} /></Field>
            {budget.trim() && (<>
              <Field id="currency" label={t("nut.currency")} error={fe.currency ? t("error.validation_failed") : undefined}><input id="currency" dir="ltr" maxLength={3} value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} /></Field>
              <Field id="region" label={t("nut.region")} error={fe.region ? t("error.validation_failed") : undefined}><input id="region" dir="ltr" value={region} onChange={(e) => setRegion(e.target.value)} /></Field>
            </>)}
            <Button type="submit" busy={busy}>{plan ? t("nut.regenerate") : t("nut.generate")}</Button>
          </form>
        </Card>
      )}

      {eligible && !plan && <Card><p className="muted">{t("nut.empty")}</p></Card>}
      {view?.kind === "needs_content" && (
        <Card><Alert kind="warning"><h2>{t("nut.content.title")}</h2><p>{t("nut.content.body")}</p></Alert>
          <ul className="plain">{(plan?.reasons ?? []).map((r) => <li key={r} className="muted">{reasonText(locale, r)}</li>)}</ul></Card>
      )}
      {view?.kind === "needs_info" && <Card><Alert kind="warning"><ul className="plain">{view.reasons.map((r) => <li key={r}>{reasonText(locale, r)}</li>)}</ul></Alert></Card>}
      {view?.kind === "referred" && <Card><Alert kind="error"><p>{t("nut.refer.body")}</p></Alert></Card>}
      {view?.kind === "unavailable" && <Card><Alert kind="error">{t("error.unexpected_status")}</Alert></Card>}
      {view?.kind === "plan" && <Card><PlanView res={view.res} wantedBudget={wantedBudget} /></Card>}
    </>
  );
}
