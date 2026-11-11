"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { ExerciseSummary } from "../../../lib/api/generated.ts";
import { LIBRARY_DIFFICULTY, LIBRARY_EQUIPMENT, LIBRARY_MUSCLES, NO_FILTERS, libraryQuery, pageCount, type Filters } from "../../../lib/exercises.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, Card, Field, Loading } from "../../../components/ui.tsx";

function Select({ id, label, value, onChange, options, prefix }: { id: string; label: string; value: string; onChange: (v: string) => void; options: readonly string[]; prefix: string }) {
  const { t } = useT();
  return (
    <Field id={id} label={label}>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{t("lib.any")}</option>
        {options.map((o) => <option key={o} value={o}>{t(`${prefix}.${o}`)}</option>)}
      </select>
    </Field>
  );
}

export default function LibraryPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [draft, setDraft] = useState<Filters>(NO_FILTERS);
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<ExerciseSummary[] | null>(null);
  const [count, setCount] = useState(0);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let live = true;
    setRows(null);
    api.call("API-EX-001", { query: libraryQuery(filters, page) }).then((r) => {
      if (!live) return;
      if (r.ok) { setRows(r.data.results ?? []); setCount(r.data.count ?? 0); setError(null); return; }
      if (r.status === 401) return router.replace(`/${locale}/login`);
      setError(r.error); setRows([]);
    });
    return () => { live = false; };
  }, [api, filters, page, router, locale]);

  function submit(e: FormEvent) { e.preventDefault(); setPage(1); setFilters(draft); }
  const active = JSON.stringify(filters) !== JSON.stringify(NO_FILTERS);
  const last = pageCount(count);

  return (
    <Card title={t("lib.title")}>
      <form onSubmit={submit} role="search">
        <Field id="q" label={t("lib.search")}><input id="q" type="search" placeholder={t("lib.searchPh")} value={draft.q} onChange={(e) => setDraft({ ...draft, q: e.target.value })} /></Field>
        <div className="row">
          <Select id="muscle" label={t("lib.muscle")} value={draft.muscle} onChange={(v) => setDraft({ ...draft, muscle: v })} options={LIBRARY_MUSCLES} prefix="muscle" />
          <Select id="equipment" label={t("lib.equipment")} value={draft.equipment} onChange={(v) => setDraft({ ...draft, equipment: v })} options={LIBRARY_EQUIPMENT} prefix="equip" />
          <Select id="difficulty" label={t("lib.difficulty")} value={draft.difficulty} onChange={(v) => setDraft({ ...draft, difficulty: v })} options={LIBRARY_DIFFICULTY} prefix="level" />
        </div>
        <div className="row">
          <Button type="submit">{t("lib.search")}</Button>
          {active && <Button type="button" onClick={() => { setDraft(NO_FILTERS); setFilters(NO_FILTERS); setPage(1); }}>{t("lib.clear")}</Button>}
        </div>
      </form>
      <ApiErrorView error={error} />
      {!rows && !error && <Loading />}
      {rows && rows.length === 0 && !error && <p>{active ? t("lib.empty") : t("lib.noneAtAll")}</p>}
      {rows && rows.length > 0 && (
        <>
          <p className="muted" aria-live="polite">{t("lib.count", { n: n(count) })}</p>
          <ul className="plain" aria-label={t("lib.title")}>
            {rows.map((r) => {
              const name = (locale === "fa" ? r.name : r.name_en) || r.name || r.name_en || r.code;
              return (
                <li key={r.id} className="doc">
                  <strong><Link href={`/${locale}/exercises/${r.id}`}>{name}</Link></strong>{" "}
                  {r.review_status === "published" ? <span className="tag">{t("lib.reviewed")}</span> : <span className="tag">{t("lib.unreviewed")}</span>}
                  <div className="muted">
                    {(r.muscles ?? []).map((m) => t(`muscle.${m}`) === `muscle.${m}` ? m : t(`muscle.${m}`)).join("، ")}
                    {r.difficulty && <> · {t(`level.${r.difficulty}`) === `level.${r.difficulty}` ? r.difficulty : t(`level.${r.difficulty}`)}</>}
                    {(r.equipment ?? []).length > 0 && <> · {(r.equipment ?? []).map((e) => t(`equip.${e}`) === `equip.${e}` ? e : t(`equip.${e}`)).join("، ")}</>}
                  </div>
                </li>
              );
            })}
          </ul>
          <nav className="row" aria-label="pagination">
            <Button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>{t("lib.prev")}</Button>
            <span className="muted">{t("lib.page", { n: n(page), m: n(last) })}</span>
            <Button type="button" disabled={page >= last} onClick={() => setPage(page + 1)}>{t("lib.next")}</Button>
          </nav>
        </>
      )}
      {rows && rows.some((r) => r.review_status !== "published") && <Alert kind="warning">{t("plan.experimental.body")}</Alert>}
    </Card>
  );
}
