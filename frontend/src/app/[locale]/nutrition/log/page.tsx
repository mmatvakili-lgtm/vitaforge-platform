"use client";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import type { ApiError } from "../../../../lib/api/client.ts";
import type { FoodSummary, MealEntry, NutritionDaySummary, RecipeSummary } from "../../../../lib/api/generated.ts";
import { MEAL_SLOTS, alertKind, buildMealRequest, defaultSlot, groupBySlot, parsePositive, type MealSource, type Slot } from "../../../../lib/nutrition-log.ts";
import { barPct, lastDates } from "../../../../lib/trends.ts";
import { rangeText } from "../../../../lib/nutrition.ts";
import { useApi, useT } from "../../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, ButtonLink, Card, Field, Loading } from "../../../../components/ui.tsx";

const today = () => new Date().toISOString().slice(0, 10);
type Kind = "food" | "recipe" | "manual";

export default function LogPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [date, setDate] = useState(today());
  const [meals, setMeals] = useState<MealEntry[] | null>(null);
  const [summary, setSummary] = useState<NutritionDaySummary | null>(null);
  const [blocked, setBlocked] = useState<"consent" | "unavailable" | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const [foods, setFoods] = useState<FoodSummary[]>([]);
  const [recipes, setRecipes] = useState<RecipeSummary[]>([]);
  const [slot, setSlot] = useState<Slot>(defaultSlot(new Date().getHours()));
  const [kind, setKind] = useState<Kind>("food");
  const [pick, setPick] = useState(""); const [amount, setAmount] = useState("");
  const [m, setM] = useState({ name: "", kcal: "", protein_g: "", carbs_g: "", fat_g: "" });
  const [water, setWater] = useState("");
  const [formErr, setFormErr] = useState(false);
  const [week, setWeek] = useState<Array<{ date: string; kcal: number; water: number; meals: number }> | null>(null);

  const fail = useCallback((e: ApiError, status: number) => {
    if (status === 401) { router.replace(`/${locale}/login`); return; }
    if (e.code === "consent_required") { setBlocked("consent"); return; }
    if (status === 409 || status === 404) { setBlocked("unavailable"); return; }
    setError(e);
  }, [router, locale]);

  const load = useCallback(async (d: string) => {
    const [a, b] = await Promise.all([api.call("API-NUT-005", { query: { date: d } }), api.call("API-NUT-008", { query: { date: d } })]);
    if (!a.ok) { setMeals([]); return fail(a.error, a.status); }
    setBlocked(null); setError(null); setMeals(a.data.meals);
    if (b.ok) setSummary(b.data); else { setSummary(null); fail(b.error, b.status); }
  }, [api, fail]);

  useEffect(() => { load(date); }, [load, date]);
  // 7-day strip from the user's own logged summaries (one request per day; days that fail are shown as empty, not guessed)
  useEffect(() => {
    let live = true;
    Promise.all(lastDates(today(), 7).map((d) => api.call("API-NUT-008", { query: { date: d } }).then((r) => ({ date: d, kcal: r.ok ? r.data.kcal : 0, water: r.ok ? r.data.water_ml : 0, meals: r.ok ? r.data.meals : 0 })))).then((w) => { if (live) setWeek(w); });
    return () => { live = false; };
  }, [api, meals]);
  useEffect(() => {
    let live = true;
    api.call("API-FOOD-001", { query: { page_size: 100 } }).then((r) => { if (live && r.ok) setFoods(r.data.results ?? []); });
    api.call("API-REC-001", { query: { page_size: 100 } }).then((r) => { if (live && r.ok) setRecipes(r.data.results ?? []); });
    const q = new URLSearchParams(window.location.search);                    // client-side read keeps the page statically exportable
    if (q.get("food")) { setKind("food"); setPick(q.get("food")!); } else if (q.get("recipe")) { setKind("recipe"); setPick(q.get("recipe")!); }
    return () => { live = false; };
  }, [api]);

  async function add(e: FormEvent) {
    e.preventDefault();
    const src: MealSource = kind === "food" ? { kind, id: pick, grams: amount } : kind === "recipe" ? { kind, id: pick, servings: amount || "1" } : { kind, ...m };
    const body = (kind !== "manual" && !pick) ? null : buildMealRequest(slot, src);
    setFormErr(!body);
    if (!body) return;
    setBusy(true); setError(null);
    const r = await api.call("API-NUT-004", { body: { ...body, ...(date !== today() ? { date } : {}) } });
    setBusy(false);
    if (!r.ok) return fail(r.error, r.status);
    setAmount(""); setM({ name: "", kcal: "", protein_g: "", carbs_g: "", fat_g: "" });
    await load(date);
  }
  async function remove(id: string) {
    const r = await api.call("API-NUT-006", { path: { meal_id: id } });
    if (!r.ok) return fail(r.error, r.status);
    await load(date);
  }
  async function addWater(ml: number) {
    setBusy(true);
    const r = await api.call("API-NUT-007", { body: { ml, ...(date !== today() ? { date } : {}) } });
    setBusy(false);
    if (!r.ok) return fail(r.error, r.status);
    setWater(""); await load(date);
  }

  if (meals === null) return <Card title={t("nut.log.title")}><Loading /></Card>;
  if (blocked === "consent") return <Card title={t("nut.log.title")}><Alert kind="warning">{t("nut.consent.needed")}</Alert><ButtonLink href={`/${locale}/onboarding?stage=consent`}>{t("nut.consent.action")}</ButtonLink></Card>;
  if (blocked === "unavailable") return <Card title={t("nut.log.title")}><Alert kind="warning">{t("nut.log.unavailable")}</Alert><ButtonLink href={`/${locale}/nutrition`}>{t("nav.nutrition")}</ButtonLink></Card>;

  const tdee = rangeText(summary?.targets.tdee); const wr = rangeText(summary?.targets.water_ml);
  const options = kind === "food" ? foods : recipes;
  const label = (x: { name_en: string; name_fa?: string }) => (locale === "fa" && x.name_fa ? x.name_fa : x.name_en);
  return (
    <>
      <Card title={t("nut.log.title")}>
        <Field id="ld" label={t("nut.log.date")}><input id="ld" type="date" max={today()} value={date} onChange={(e) => e.target.value && setDate(e.target.value)} dir="ltr" /></Field>
        <ApiErrorView error={error} />
        {summary && (
          <section aria-label={t("nut.log.summary")}>
            <h2>{t("nut.log.summary")}</h2>
            <ul className="plain">
              <li>{t("nutrient.kcal")}: <bdi>{n(Math.round(summary.kcal))}</bdi>{tdee && <span className="muted"> / {n(tdee[0])}–{n(tdee[1])}</span>}</li>
              {summary.protein_g !== undefined && <li>{t("nutrient.protein_g")}: {n(Math.round(summary.protein_g))} g</li>}
              {summary.carbs_g !== undefined && <li>{t("nutrient.carbs_g")}: {n(Math.round(summary.carbs_g))} g</li>}
              {summary.fat_g !== undefined && <li>{t("nutrient.fat_g")}: {n(Math.round(summary.fat_g))} g</li>}
              <li>{t("nut.log.water")}: {n(summary.water_ml)} ml{wr && <span className="muted"> / {n(wr[0])}–{n(wr[1])}</span>}</li>
            </ul>
            {summary.note && <p className="muted">{summary.note}</p>}
            <p className="muted">{t("nut.label.estimate")}</p>
          </section>
        )}
        {meals.length === 0 && <p className="muted">{t("nut.log.empty")}</p>}
        {groupBySlot(meals).map((g) => (
          <section key={g.slot}>
            <h2>{t(`nut.slot.${g.slot}`)}</h2>
            <ul className="plain">
              {g.meals.map((e) => {
                const a = alertKind(e);
                return (
                  <li key={e.id}>
                    <strong>{(locale === "fa" && e.name_fa) || e.name}</strong> — {e.kcal !== undefined ? `${n(Math.round(e.kcal))} ${t("nutrient.kcal.unit")}` : t("nut.log.noKcal")}
                    {e.source === "catalog" && e.review_status !== "reviewed" && <span className="badge badge-warn"> {t("lib.unreviewed")}</span>}
                    {a === "allergen" && <Alert kind="error">{t("nut.log.allergenAlert", { list: ((e.allergen_alert as { allergens: string[] }).allergens).map((x) => t(`allergen.${x}`)).join("، ") })}</Alert>}
                    {a === "unknown" && <Alert kind="warning">{t("nut.log.allergenUnknown")}</Alert>}
                    {e.missing_nutrients.length > 0 && <span className="muted"> · {t("nut.meal.missing", { list: e.missing_nutrients.map((k) => t(`nutrient.${k}`)).join("، ") })}</span>}
                    {" "}<button type="button" className="linklike" onClick={() => remove(e.id)}>{t("nut.log.remove")}</button>
                  </li>);
              })}
            </ul>
          </section>
        ))}
      </Card>

      {week && week.some((d) => d.meals > 0 || d.water > 0) && (
        <Card title={t("nut.log.week")}>
          <ol className="bars">
            {week.map((d) => (
              <li key={d.date} title={t("nut.log.week.item", { kcal: Math.round(d.kcal), ml: d.water })}>
                <span className="bar" style={{ blockSize: `${barPct(d.kcal, Math.max(...week.map((x) => x.kcal)))}%` }} />
                <span className="muted bar-label"><time dateTime={d.date}>{new Intl.DateTimeFormat(locale === "fa" ? "fa-IR" : "en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(d.date))}</time></span>
                <span className="sr-only">{t("nut.log.week.item", { kcal: Math.round(d.kcal), ml: d.water })}</span>
              </li>))}
          </ol>
          <p className="muted">{t("nut.log.week.hint")}</p>
        </Card>
      )}

      <Card title={t("nut.log.add")}>
        <form onSubmit={add} noValidate>
          <Field id="slot" label={t("nut.log.slot")}><select id="slot" value={slot} onChange={(e) => setSlot(e.target.value as Slot)}>{MEAL_SLOTS.map((s) => <option key={s} value={s}>{t(`nut.slot.${s}`)}</option>)}</select></Field>
          <Field id="kind" label={t("nut.log.source")}>
            <select id="kind" value={kind} onChange={(e) => { setKind(e.target.value as Kind); setPick(""); setAmount(""); }}>
              <option value="food">{t("foods.tab.foods")}</option><option value="recipe">{t("foods.tab.recipes")}</option><option value="manual">{t("nut.log.manual")}</option>
            </select>
          </Field>
          {kind !== "manual" ? (
            <>
              <Field id="pick" label={t(kind === "food" ? "foods.tab.foods" : "foods.tab.recipes")}>
                <select id="pick" value={pick} onChange={(e) => setPick(e.target.value)}><option value="" />{options.map((x) => <option key={x.id} value={x.id}>{label(x)}{x.review_status !== "reviewed" ? ` (${t("lib.unreviewed")})` : ""}</option>)}</select>
              </Field>
              {options.length === 0 && <p className="muted">{t("foods.empty.body")}</p>}
              <Field id="amt" label={t(kind === "food" ? "nut.log.grams" : "nut.log.servings")}><input id="amt" inputMode="decimal" dir="ltr" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder={kind === "recipe" ? "1" : ""} /></Field>
            </>
          ) : (
            <>
              <p className="hint">{t("nut.log.manual.hint")}</p>
              <Field id="mn" label={t("nut.log.name")}><input id="mn" value={m.name} onChange={(e) => setM({ ...m, name: e.target.value })} maxLength={80} /></Field>
              {(["kcal", "protein_g", "carbs_g", "fat_g"] as const).map((k) => (
                <Field key={k} id={`m-${k}`} label={`${t(`nutrient.${k}`)} (${t(`nutrient.${k}.unit`)})`}><input id={`m-${k}`} inputMode="decimal" dir="ltr" value={m[k]} onChange={(e) => setM({ ...m, [k]: e.target.value })} /></Field>))}
            </>
          )}
          {formErr && <p className="field-error" role="alert">{t("error.validation_failed")}</p>}
          <Button type="submit" busy={busy}>{t("nut.log.addBtn")}</Button>
        </form>
      </Card>

      <Card title={t("nut.log.water")}>
        <div className="row">
          {[250, 500].map((ml) => <Button key={ml} type="button" busy={busy} onClick={() => addWater(ml)}>+{n(ml)} ml</Button>)}
          <input aria-label={t("nut.log.water")} inputMode="numeric" dir="ltr" value={water} onChange={(e) => setWater(e.target.value)} />
          <Button type="button" busy={busy} disabled={!parsePositive(water)} onClick={() => addWater(parsePositive(water)!)}>{t("nut.log.addBtn")}</Button>
        </div>
      </Card>
    </>
  );
}
