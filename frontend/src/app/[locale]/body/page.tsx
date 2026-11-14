"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { BodyOverview } from "../../../lib/api/generated.ts";
import { BODY_METRICS, BODY_METRIC_KEYS, parseMeasurement, type BodyMetric } from "../../../lib/body.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, Card, Field, Loading } from "../../../components/ui.tsx";

export default function BodyPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [ov, setOv] = useState<BodyOverview | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [metric, setMetric] = useState<BodyMetric>("weight");
  const [value, setValue] = useState("");
  const [source, setSource] = useState<"measured" | "estimated">("measured");
  const [fieldErr, setFieldErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  async function load() {
    const r = await api.call("API-BODY-001");
    if (r.ok) return setOv(r.data);
    if (r.status === 401) return router.replace(`/${locale}/login`);
    setError(r.error); setOv({});
  }
  useEffect(() => { void load(); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaved(false); setError(null);
    const v = parseMeasurement(metric, value);
    if (v === null) return setFieldErr(t("body.invalid", { min: n(BODY_METRICS[metric].min), max: n(BODY_METRICS[metric].max), unit: BODY_METRICS[metric].unit }));
    setFieldErr(""); setBusy(true);
    const r = await api.call("API-BODY-002", { body: { metric, value: v, unit: BODY_METRICS[metric].unit, source } });
    setBusy(false);
    if (!r.ok) { if (r.status === 401) return router.replace(`/${locale}/login`); return setError(r.error); }
    setSaved(true); setValue("");
    await load();
  }

  const latest = (ov?.latest ?? {}) as Record<string, number>;
  return (
    <Card title={t("body.title")}>
      <ApiErrorView error={error} />
      {!ov && !error && <Loading />}
      {ov && (
        <>
          {Object.keys(latest).length === 0 ? <p className="muted">{t("body.empty")}</p> : (
            <ul className="plain">
              {BODY_METRIC_KEYS.filter((k) => latest[k] !== undefined).map((k) => <li key={k}>{t(`body.metric.${k}`)}: {n(latest[k])} {BODY_METRICS[k].unit}</li>)}
            </ul>)}
          {(ov.bmi || ov.whtr) && (
            <ul className="plain">
              {ov.bmi?.value !== undefined && <li>{t("body.bmi")}: {n(ov.bmi.value)}</li>}
              {ov.whtr?.value !== undefined && <li>{t("body.whtr")}: {n(ov.whtr.value)}</li>}
            </ul>)}
          {(ov.bmi || ov.whtr) && <p className="muted">{t("body.screeningNote")}</p>}
          <form onSubmit={submit} noValidate>
            <Field id="metric" label={t("body.metric")}>
              <select id="metric" value={metric} onChange={(e) => { setMetric(e.target.value as BodyMetric); setFieldErr(""); }}>
                {BODY_METRIC_KEYS.map((k) => <option key={k} value={k}>{t(`body.metric.${k}`)} ({BODY_METRICS[k].unit})</option>)}
              </select>
            </Field>
            <Field id="value" label={t("body.value")} error={fieldErr}>
              <input id="value" inputMode="decimal" dir="ltr" autoComplete="off" value={value} onChange={(e) => setValue(e.target.value)} aria-invalid={!!fieldErr} />
            </Field>
            <Field id="source" label={t("body.source")}>
              <select id="source" value={source} onChange={(e) => setSource(e.target.value as "measured" | "estimated")}>
                <option value="measured">{t("body.source.measured")}</option>
                <option value="estimated">{t("body.source.estimated")}</option>
              </select>
            </Field>
            <Button type="submit" busy={busy}>{t("body.save")}</Button>
            {saved && <Alert kind="success">{t("body.saved")}</Alert>}
          </form>
        </>
      )}
    </Card>
  );
}
