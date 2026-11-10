"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { ApiError } from "../../../../lib/api/client.ts";
import type { ExerciseDetail } from "../../../../lib/api/generated.ts";
import { useApi, useT } from "../../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Card, Loading } from "../../../../components/ui.tsx";

export default function ExercisePage() {
  const { locale, t } = useT();
  const api = useApi();
  const router = useRouter();
  const id = String(useParams<{ id: string }>()?.id ?? "");
  const [ex, setEx] = useState<ExerciseDetail | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let live = true;
    api.call("API-EX-002", { path: { exercise_id: id } }).then((r) => {
      if (!live) return;
      if (r.ok) return setEx(r.data);
      if (r.status === 401) return router.replace(`/${locale}/login`);
      setError(r.error);
    });
    return () => { live = false; };
  }, [api, id, router, locale]);

  const reviewed = ex?.review_status === "published";
  const name = ex ? (locale === "fa" ? ex.name : ex.name_en) || ex.name || ex.name_en : "";
  return (
    <Card title={name || t("ex.title")}>
      <ApiErrorView error={error} />
      {!ex && !error && <Loading />}
      {ex && (
        <div>
          {!reviewed && <Alert kind="warning">{t("ex.unreviewed")}</Alert>}
          {ex.description && <p>{ex.description}</p>}
          {ex.compatibility?.status && <p><strong>{t("ex.compat")}:</strong> {t(`ex.compat.${ex.compatibility.status}`)}</p>}
          {(ex.steps ?? []).length > 0 && (<><h2>{t("ex.steps")}</h2><ol>{ex.steps!.map((s, i) => <li key={i}>{s}</li>)}</ol></>)}
          {ex.breathing && (<><h2>{t("ex.breathing")}</h2><p>{ex.breathing}</p></>)}
          {(ex.common_mistakes ?? []).length > 0 && (<><h2>{t("ex.mistakes")}</h2><ul>{ex.common_mistakes!.map((s, i) => <li key={i}>{s}</li>)}</ul></>)}
          {ex.safety_notes && (<><h2>{t("ex.safety")}</h2><p>{ex.safety_notes}</p></>)}
          {(ex.media ?? []).map((m, i) => (m.type === "image" && m.url ? <img key={i} src={m.url} alt={name} loading="lazy" style={{ maxInlineSize: "100%" }} /> : null))}
          <p className="muted">{t("ex.review")}: <bdi dir="ltr">{ex.review_status}</bdi></p>
        </div>
      )}
      <p><Link href={`/${locale}/plan`}>{t("ex.back")}</Link></p>
    </Card>
  );
}
