"use client";
import type { SafetyDecision } from "../lib/api/generated.ts";
import { safetyReason } from "../lib/i18n.ts";
import { useT } from "../lib/react/context.tsx";
import { Alert, ButtonLink } from "./ui.tsx";

const ACTION: Record<string, string> = { NEEDS_INFO: "screening", BLOCK_CONSENT: "consent" };

/** Renders a non-plan Safety Core outcome. Texts are keyed by status; reasons come from the generated safety catalog. */
export function DecisionPanel({ decision }: { decision: SafetyDecision }) {
  const { locale, t } = useT();
  const k = `decision.${decision.status}`;
  const known = t(`${k}.title`) !== `${k}.title`;
  const title = known ? t(`${k}.title`) : t("decision.blocked.title");
  const body = known ? t(`${k}.body`) : t("decision.blocked.body");
  const action = ACTION[decision.status];
  const reasons = decision.reasons ?? [];
  const questions = decision.required_questions ?? [];
  const ref = decision.referral;
  return (
    <div className="decision" data-status={decision.status}>
      <Alert kind={decision.status === "NEEDS_INFO" ? "warning" : "error"}>
        <h2>{title}</h2>
        <p>{body}</p>
      </Alert>
      {questions.length > 0 && (
        <ul className="plain">{questions.map((q) => <li key={q}>{t(`screening.q.${q}`) === `screening.q.${q}` ? q : t(`screening.q.${q}`)}</li>)}</ul>
      )}
      {reasons.length > 0 && (
        <>
          <h3>{t("decision.reasons")}</h3>
          <ul>{reasons.map((r, i) => <li key={`${r.code}-${i}`}>{safetyReason(locale, r.code ?? r.message_key ?? "")}</li>)}</ul>
        </>
      )}
      {ref && (
        <Alert kind="info">
          <p>{ref.urgency === "urgent" ? t("decision.referral.urgent") : t("decision.referral.non_urgent")}</p>
          {ref.content_status !== "clinical_reviewed" && ref.content_status !== "published" && <p className="muted">{t("decision.referral.unreviewed")}</p>}
        </Alert>
      )}
      {action && <ButtonLink href={`/${locale}/onboarding?stage=${action}`}>{t(`${k}.action`)}</ButtonLink>}
      <p className="muted">{t("decision.id")}: <bdi dir="ltr">{decision.decision_id}</bdi></p>
    </div>
  );
}
