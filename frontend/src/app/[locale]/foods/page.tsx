"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { FoodDetail, FoodSummary, RecipeDetail, RecipeSummary } from "../../../lib/api/generated.ts";
import { DIET_TAGS, nutrientLines } from "../../../lib/nutrition.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, ButtonLink, Card, Field, Loading } from "../../../components/ui.tsx";

type Tab = "foods" | "recipes";
type Diet = (typeof DIET_TAGS)[number];

function Nutrients({ v, basis }: { v: Record<string, unknown>; basis: string }) {
  const { t, n } = useT();
  const lines = nutrientLines(v);
  if (!lines.length) return <p className="muted">{t("foods.noNutrients")}</p>;
  return (<><p className="hint">{basis}</p><ul className="plain">{lines.map((l) => <li key={l.key}>{t(`nutrient.${l.key}`)}: <bdi>{n(Math.round(l.value * 10) / 10)}</bdi> {t(`nutrient.${l.key}.unit`)}</li>)}</ul></>);
}

function Allergens({ list, known }: { list?: string[]; known?: boolean }) {
  const { t } = useT();
  return (<p className="allergens">{(list ?? []).length > 0 ? t("nut.meal.allergens", { list: list!.map((a) => t(`allergen.${a}`)).join("، ") }) : t("nut.meal.noAllergens")}
    {known === false && <strong> — {t("nut.meal.allergensUnknown")}</strong>}</p>);
}

function ReviewBadge({ status }: { status: string }) {
  const { t } = useT();
  return <span className={status === "reviewed" ? "badge badge-ok" : "badge badge-warn"}>{status === "reviewed" ? t("lib.reviewed") : t("lib.unreviewed")}</span>;
}

export default function FoodsPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("foods");
  const [draft, setDraft] = useState({ q: "", diet: "" as "" | Diet });
  const [filters, setFilters] = useState(draft);
  const [foods, setFoods] = useState<FoodSummary[] | null>(null);
  const [recipes, setRecipes] = useState<RecipeSummary[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [fd, setFd] = useState<FoodDetail | null>(null);
  const [rd, setRd] = useState<RecipeDetail | null>(null);
  const [avoid, setAvoid] = useState<string[]>([]);
  const [error, setError] = useState<ApiError | null>(null);

  // The user's saved allergens are always excluded from browsing results unless the server cannot tell us them.
  useEffect(() => {
    let live = true;
    api.call("API-NUT-002").then((r) => { if (live && r.ok) setAvoid(r.data.allergens ?? []); });
    return () => { live = false; };
  }, [api]);

  useEffect(() => {
    let live = true;
    setError(null); setOpen(null); setFd(null); setRd(null);
    const query = { page_size: 50, ...(filters.q.trim() ? { q: filters.q.trim() } : {}), ...(filters.diet ? { diet: filters.diet } : {}), ...(avoid.length ? { avoid_allergens: avoid.join(",") } : {}) };
    const done = (status: number, e?: ApiError) => { if (status === 401) { router.replace(`/${locale}/login`); return true; } if (e) setError(e); return false; };
    if (tab === "foods") {
      setFoods(null);
      api.call("API-FOOD-001", { query }).then((r) => { if (!live) return; if (r.ok) setFoods(r.data.results ?? []); else { done(r.status, r.error); setFoods([]); } });
    } else {
      setRecipes(null);
      api.call("API-REC-001", { query }).then((r) => { if (!live) return; if (r.ok) setRecipes(r.data.results ?? []); else { done(r.status, r.error); setRecipes([]); } });
    }
    return () => { live = false; };
  }, [api, tab, filters, avoid, router, locale]);

  async function toggle(id: string) {
    if (open === id) { setOpen(null); return; }
    setOpen(id); setFd(null); setRd(null);
    if (tab === "foods") { const r = await api.call("API-FOOD-002", { path: { food_id: id } }); if (r.ok) setFd(r.data); else setError(r.error); }
    else { const r = await api.call("API-REC-002", { path: { recipe_id: id } }); if (r.ok) setRd(r.data); else setError(r.error); }
  }
  function submit(e: FormEvent) { e.preventDefault(); setFilters(draft); }
  const rows = tab === "foods" ? foods : recipes;
  const name = (x: { name_en: string; name_fa?: string }) => (locale === "fa" && x.name_fa ? x.name_fa : x.name_en);

  return (
    <Card title={t("foods.title")}>
      <p>{t("foods.intro")}</p>
      <div className="row" role="tablist">
        <Button type="button" role="tab" aria-selected={tab === "foods"} onClick={() => setTab("foods")}>{t("foods.tab.foods")}</Button>
        <Button type="button" role="tab" aria-selected={tab === "recipes"} onClick={() => setTab("recipes")}>{t("foods.tab.recipes")}</Button>
        <ButtonLink href={`/${locale}/nutrition/log`} secondary>{t("nut.log.title")}</ButtonLink>
      </div>
      {avoid.length > 0 && <Alert kind="info">{t("foods.avoiding", { list: avoid.map((a) => t(`allergen.${a}`)).join("، ") })}</Alert>}
      <form onSubmit={submit} role="search">
        <Field id="fq" label={t("lib.search")}><input id="fq" type="search" value={draft.q} onChange={(e) => setDraft({ ...draft, q: e.target.value })} /></Field>
        <Field id="fdiet" label={t("nut.diet")}>
          <select id="fdiet" value={draft.diet} onChange={(e) => setDraft({ ...draft, diet: e.target.value as "" | Diet })}><option value="">{t("lib.any")}</option>{DIET_TAGS.map((d) => <option key={d} value={d}>{t(`diet.${d}`)}</option>)}</select>
        </Field>
        <Button type="submit">{t("lib.search")}</Button>
      </form>
      <ApiErrorView error={error} />
      {rows === null && <Loading />}
      {rows && rows.length === 0 && !error && <Alert kind="info"><strong>{t("foods.empty.title")}</strong> {t("foods.empty.body")}</Alert>}
      <ul className="plain">
        {(rows ?? []).map((x) => (
          <li key={x.id} className="card-lite">
            <button type="button" className="linklike" aria-expanded={open === x.id} onClick={() => toggle(x.id)}>{name(x)}</button> <ReviewBadge status={x.review_status} />
            {"per_100g" in x && tab === "foods" && x.per_100g.kcal !== undefined && <span className="muted"> · {n(Math.round(x.per_100g.kcal))} {t("nutrient.kcal.unit")}/{n(100)}g</span>}
            {"per_serving" in x && tab === "recipes" && x.per_serving.kcal !== undefined && <span className="muted"> · {n(Math.round(x.per_serving.kcal))} {t("nutrient.kcal.unit")}/{t("foods.serving")}</span>}
            <Allergens list={x.allergens} known={x.allergens_known} />
            {open === x.id && tab === "foods" && (fd ? (
              <div>
                <Nutrients v={fd.per_100g} basis={t("foods.per100")} />
                {fd.source && <p className="muted">{t("foods.source")}: {fd.source.dataset} {fd.source.license ? `(${fd.source.license}${fd.source.license_verified ? "" : ` — ${t("foods.licenseUnverified")}`})` : ""}</p>}
                {!fd.source && <p className="muted">{t("foods.noSource")}</p>}
                {(fd.notes ?? []).map((m) => <p key={m} className="muted">{m}</p>)}
                <ButtonLink href={`/${locale}/nutrition/log?food=${encodeURIComponent(fd.id)}`} secondary>{t("foods.logIt")}</ButtonLink>
              </div>) : <Loading />)}
            {open === x.id && tab === "recipes" && (rd ? (
              <div>
                <Nutrients v={rd.per_serving} basis={t("foods.perServing")} />
                {(rd.missing_nutrients ?? []).length > 0 && <p className="muted">{t("nut.meal.missing", { list: rd.missing_nutrients!.map((k) => t(`nutrient.${k}`)).join("، ") })}</p>}
                <h3>{t("nut.meal.ingredients")}</h3>
                <ul className="plain">{rd.ingredients.map((i) => <li key={i.food_id}>{(locale === "fa" && i.name_fa) || i.name_en} — {n(i.grams ?? 0)} g</li>)}</ul>
                <h3>{t("nut.meal.steps")}</h3>
                {(rd.steps ?? []).length ? <ol>{rd.steps!.map((s, k) => <li key={k}>{s}</li>)}</ol> : <p className="muted">{t("nut.meal.noSteps")}</p>}
                <ButtonLink href={`/${locale}/nutrition/log?recipe=${encodeURIComponent(rd.id)}`} secondary>{t("foods.logIt")}</ButtonLink>
              </div>) : <Loading />)}
          </li>
        ))}
      </ul>
    </Card>
  );
}
